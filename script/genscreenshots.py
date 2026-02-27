#!/usr/bin/env -S uv run python3
"""
OG Image Generator using Playwright screenshots.

Two modes determined by section:
- Template mode (bannerSections like blog, crumb): screenshots the banner template at /{path}/banner.html
- Page mode (all other sections): screenshots the rendered page with injected CSS to hide chrome

Discovers content from markdown files, caches via MD5 of file content, and only
regenerates when source changes.

Usage:
  script/genscreenshots.py              # Generate all missing/changed banners
  script/genscreenshots.py --staged-only # Only process git-staged content files
"""

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import tomllib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import frontmatter

from blog.optimize_png import optimize_files

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class ScreenshotMode(Enum):
    TEMPLATE = "template"
    PAGE = "page"

    @staticmethod
    def for_section(section: str, banner_sections: list[str]) -> "ScreenshotMode":
        return (
            ScreenshotMode.TEMPLATE
            if section in banner_sections
            else ScreenshotMode.PAGE
        )


@dataclass
class ContentFile:
    path: Path
    section: str


# ---------------------------------------------------------------------------
# Pure functions (tested without Hugo/Playwright)
# ---------------------------------------------------------------------------

# CSS injected into page-mode screenshots to hide site chrome and add branding
HIDE_CHROME_CSS = """
header, nav, footer, .mobile-menu-toggle, .sidebar, .menu,
.prev-next-nav, .post-meta, .page-header { display: none !important; }
main { margin: 0 !important; padding: 1.5rem !important; padding-top: 4rem !important; }
body { overflow: hidden !important; }
"""

# JS injected into page-mode screenshots to add "bjorn.now" branding
# Matches the masthead style from single.banner.html
BRANDING_JS = """
(() => {
    const el = document.createElement('div');
    el.textContent = 'bjorn.now';
    el.style.cssText = `
        position: fixed; top: 0; left: 0; right: 0;
        padding: 0.6rem 1.5rem;
        font-size: 24px; font-weight: 800;
        font-family: Avenir, Montserrat, Corbel, 'URW Gothic', source-sans-pro, sans-serif;
        letter-spacing: -0.02em;
        color: white;
        text-decoration: underline;
        text-decoration-color: #9E9EFF;
        text-decoration-thickness: 3px;
        text-underline-offset: 5px;
        z-index: 99999;
    `;
    document.body.prepend(el);
})();
"""


def parse_hugo_list(csv_text: str) -> dict[str, str]:
    """Parse `hugo list all` CSV output into {content_path: url_path} mapping.

    Only includes regular pages (kind=page), excludes drafts.
    """
    result = {}
    reader = csv.DictReader(csv_text.strip().splitlines())
    for row in reader:
        if row.get("kind") != "page":
            continue
        if row.get("draft") == "true":
            continue
        path = row.get("path", "")
        permalink = row.get("permalink", "")
        if path and permalink:
            url_path = urlparse(permalink).path
            result[path] = url_path
    return result


class BannerPath:
    @staticmethod
    def for_content(cf: ContentFile) -> Path:
        """Derive banner image path from content file. Uses ContentBaseName (filename without .md)."""
        return Path("assets/img/banners") / f"{cf.path.stem}.png"


def should_skip(front_matter: dict) -> bool:
    """Check if a post should be skipped (has custom image or is a draft)."""
    if front_matter.get("draft"):
        return True

    # Skip if post has a custom image
    if front_matter.get("image"):
        return True

    # Skip if post has a non-empty images array
    images = front_matter.get("images")
    if images and len(images) > 0:
        return True

    return False


def check_cache(
    cache: dict,
    banner_path: Path,
    content_hash: str,
    check_file: bool = False,
) -> bool:
    """Check if a banner is up-to-date in the cache.

    Returns True if the cached hash matches and (optionally) the file exists.
    """
    key = str(banner_path)
    entry = cache.get(key, {})
    if entry.get("content_hash") != content_hash:
        return False
    if check_file and not banner_path.exists():
        return False
    return True


def calculate_content_hash(path: Path) -> str:
    """Calculate MD5 hash of a file's content."""
    return hashlib.md5(path.read_text().encode()).hexdigest()


def discover_sections(content_dir: Path) -> list[str]:
    """Auto-discover content sections from the filesystem.

    A section is a subdirectory of content/ that contains at least one .md file
    (excluding _index.md).
    """
    sections = []
    for entry in sorted(content_dir.iterdir()):
        if not entry.is_dir():
            continue
        # Check for at least one non-index markdown file
        has_content = any(
            f.suffix == ".md" and f.name != "_index.md" for f in entry.iterdir()
        )
        if has_content:
            sections.append(entry.name)
    return sections


def parse_staged_files(git_output: str) -> list[Path]:
    """Parse git diff output to find staged content files."""
    result = []
    for line in git_output.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("content/") and line.endswith(".md"):
            p = Path(line)
            if p.name != "_index.md":
                result.append(p)
    return result


# ---------------------------------------------------------------------------
# I/O and orchestration (not unit-tested)
# ---------------------------------------------------------------------------


def load_hugo_config(project_root: Path) -> dict:
    """Load hugo.toml and return the parsed config."""
    config_path = project_root / "hugo.toml"
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def get_url_map(project_root: Path) -> dict[str, str]:
    """Run `hugo list all` and return {content_path: url_path} mapping."""
    result = subprocess.run(
        ["hugo", "list", "all"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    if result.returncode != 0:
        raise RuntimeError(f"hugo list all failed:\n{result.stderr}")
    return parse_hugo_list(result.stdout)


def collect_content_files(
    project_root: Path,
    sections: list[str],
    url_map: dict[str, str],
    staged_only: Optional[list[Path]] = None,
) -> list[ContentFile]:
    """Scan content directories and return ContentFile objects for eligible posts."""
    content_dir = project_root / "content"
    results = []

    for section in sections:
        section_dir = content_dir / section
        if not section_dir.is_dir():
            continue

        for md_file in sorted(section_dir.glob("*.md")):
            if md_file.name == "_index.md":
                continue

            # If --staged-only, skip files not in the staged list
            rel_path = md_file.relative_to(project_root)
            if staged_only is not None and rel_path not in staged_only:
                continue

            # Skip files not in the URL map (e.g. drafts that Hugo excluded)
            if str(rel_path) not in url_map:
                continue

            try:
                post = frontmatter.load(str(md_file))
            except Exception as e:
                print(f"Warning: could not parse {md_file}: {e}")
                continue

            fm = post.metadata
            if should_skip(fm):
                continue

            results.append(
                ContentFile(
                    path=rel_path,
                    section=section,
                )
            )

    return results


def start_hugo(project_root: Path, port: int) -> subprocess.Popen:
    """Start hugo server and wait until it's ready."""
    proc = subprocess.Popen(
        [
            "hugo",
            "server",
            "--disableLiveReload",
            "--port",
            str(port),
            "--bind",
            "127.0.0.1",
        ],
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    # Poll until Hugo is serving
    import urllib.request

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1)
            return proc
        except Exception:
            if proc.poll() is not None:
                output = proc.stdout.read().decode() if proc.stdout else ""
                raise RuntimeError(f"Hugo exited early:\n{output}")
            time.sleep(0.3)

    proc.terminate()
    raise RuntimeError("Hugo did not become ready within 30 seconds")


def take_screenshot(
    page,
    url: str,
    output_path: Path,
    mode: ScreenshotMode,
) -> None:
    """Navigate to URL and take a screenshot with Playwright."""
    page.goto(url, wait_until="networkidle")

    if mode == ScreenshotMode.TEMPLATE:
        # Template mode: screenshot the banner template as-is
        pass
    else:
        # Page mode: inject CSS to hide site chrome, add branding
        page.add_style_tag(content=HIDE_CHROME_CSS)
        page.evaluate(BRANDING_JS)
        page.wait_for_timeout(100)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(output_path))


def generate_all(args):
    """Main generation pipeline."""
    project_root = Path(args.project_root)
    config = load_hugo_config(project_root)
    banner_sections = config.get("params", {}).get("bannerSections", [])
    content_dir = project_root / "content"

    # Discover sections
    sections = discover_sections(content_dir)
    print(f"Discovered sections: {', '.join(sections)}")

    # Get URL map from Hugo
    print("Getting URL map from Hugo...")
    url_map = get_url_map(project_root)
    print(f"Found {len(url_map)} pages in Hugo.")

    # Handle --staged-only
    staged_paths = None
    if args.staged_only:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        staged_paths = parse_staged_files(result.stdout)
        if not staged_paths:
            print("No staged content files found, nothing to do.")
            return 0
        print(f"Staged content files: {len(staged_paths)}")

    # Collect eligible content files
    content_files = collect_content_files(project_root, sections, url_map, staged_paths)
    if not content_files:
        print("No content files need processing.")
        return 0

    # Load cache
    cache_path = project_root / args.cache_file
    cache = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text())
        except json.JSONDecodeError:
            print("Warning: cache file corrupted, starting fresh.")

    # Determine which files need regeneration
    to_generate = []
    for cf in content_files:
        source_path = project_root / cf.path
        if not source_path.exists():
            continue

        content_hash = calculate_content_hash(source_path)
        banner_path = BannerPath.for_content(cf)
        abs_banner = project_root / banner_path

        if check_cache(cache, banner_path, content_hash, check_file=True):
            continue

        to_generate.append((cf, content_hash, banner_path))

    if not to_generate:
        print("All banners are up-to-date.")
        return 0

    print(f"Need to generate {len(to_generate)} banner(s).")

    # Start Hugo server
    port = args.port
    print(f"Starting Hugo server on port {port}...")
    hugo_proc = start_hugo(project_root, port)
    base_url = f"http://127.0.0.1:{port}"

    try:
        # Launch Playwright
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            context = browser.new_context(
                viewport={"width": 1200, "height": 630},
                device_scale_factor=1,
                color_scheme="dark",
            )
            page = context.new_page()

            generated_banners = []
            for cf, content_hash, banner_path in to_generate:
                url_path = url_map.get(str(cf.path))
                if not url_path:
                    print(f"  Warning: no URL found for {cf.path}, skipping")
                    continue

                mode = ScreenshotMode.for_section(cf.section, banner_sections)

                if mode == ScreenshotMode.TEMPLATE:
                    full_url = f"{base_url}{url_path}banner.html"
                else:
                    full_url = f"{base_url}{url_path}"

                abs_banner = project_root / banner_path
                print(f"  [{mode.value}] {cf.path} -> {banner_path}")

                try:
                    take_screenshot(page, full_url, abs_banner, mode)
                except Exception as e:
                    print(f"  Error screenshotting {cf.path}: {e}")
                    continue

                # Update cache
                cache[str(banner_path)] = {"content_hash": content_hash}
                generated_banners.append(abs_banner)

            browser.close()

        # Optimize PNGs losslessly
        if generated_banners:
            count, total_before, total_after = optimize_files(generated_banners)
            saved = total_before - total_after
            pct = (saved / total_before * 100) if total_before else 0
            print(f"Optimized {count} PNG(s): saved {saved // 1024}K ({pct:.0f}%)")

        # Save cache
        cache_path.write_text(json.dumps(cache, indent=2) + "\n")
        print(f"Cache saved to {cache_path}")

        # Auto-stage generated banners if --staged-only
        if args.staged_only and generated_banners:
            git_add_cmd = ["git", "add"] + [str(b) for b in generated_banners]
            subprocess.run(git_add_cmd, cwd=project_root, check=True)
            # Also stage the cache file
            subprocess.run(
                ["git", "add", str(cache_path)],
                cwd=project_root,
                check=True,
            )
            print(f"Auto-staged {len(generated_banners)} banner(s) and cache file.")

        print(f"Done. Generated {len(generated_banners)} banner(s).")
        return 0

    finally:
        hugo_proc.terminate()
        try:
            hugo_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            hugo_proc.kill()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate OG images via Playwright screenshots"
    )
    parser.add_argument(
        "--staged-only",
        action="store_true",
        help="Only process git-staged content files, auto-stage generated PNGs",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=1314,
        help="Hugo server port (default: 1314, avoids conflict with dev server on 1313)",
    )
    parser.add_argument(
        "--cache-file",
        default=".banner-cache",
        help="Path to cache file (default: .banner-cache)",
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root directory (default: current directory)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        sys.exit(generate_all(args))
    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == "__main__":
    main()
