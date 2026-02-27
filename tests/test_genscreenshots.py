"""
Tests for the screenshot-based OG image generator.

Tests pure logic without requiring Hugo or Playwright:
- Hugo list output parsing (URL mapping)
- Mode selection (template vs page)
- Banner path derivation
- Cache hit/miss logic
- Front matter filtering (custom images, drafts)
- Section auto-discovery
- Staged file parsing
"""

import hashlib
import textwrap
from pathlib import Path

import pytest
from genscreenshots import (
    BannerPath,
    ContentFile,
    ScreenshotMode,
    calculate_content_hash,
    check_cache,
    discover_sections,
    parse_hugo_list,
    parse_staged_files,
    should_skip,
)


class TestParseHugoList:
    """Test parsing of `hugo list all` CSV output into URL map."""

    SAMPLE_CSV = textwrap.dedent(
        """\
        path,slug,title,date,expiryDate,publishDate,draft,permalink,kind,section
        content/blog/2025-07-which-hats-are-you-wearing.md,,Which hat are you wearing?,2025-07-12T15:06:00+08:00,0001-01-01T00:00:00Z,2025-07-12T15:06:00+08:00,false,https://bjorn.now/blog/2025/07/12/which-hat-are-you-wearing/,page,blog
        content/til/2025-08-01-macos-fingerprint-reader-sudo.md,,Enabling macOS fingerprint reader for sudo,2025-08-01T23:15:00+08:00,0001-01-01T00:00:00Z,2025-08-01T23:15:00+08:00,false,https://bjorn.now/til/2025-08-01-macos-fingerprint-reader-sudo/,page,til
        content/scrap/2025-09-03T132628.md,,,2025-09-03T13:26:28+02:00,0001-01-01T00:00:00Z,2025-09-03T13:26:28+02:00,false,https://bjorn.now/scrap/2025-09-03t132628/,page,scrap
        content/blog/_index.md,,Posts,2024-05-04T00:00:00Z,0001-01-01T00:00:00Z,2024-05-04T00:00:00Z,false,https://bjorn.now/blog/,section,blog
        content/blog/2025-09-12-unique-ids-when-testing.md,,Draft Post,2025-09-12T10:06:50+02:00,0001-01-01T00:00:00Z,2025-09-12T10:06:50+02:00,true,https://bjorn.now/blog/2025/09/12/draft-post/,page,blog
    """
    )

    def test_extracts_page_urls(self):
        url_map = parse_hugo_list(self.SAMPLE_CSV)
        assert (
            url_map["content/blog/2025-07-which-hats-are-you-wearing.md"]
            == "/blog/2025/07/12/which-hat-are-you-wearing/"
        )

    def test_handles_non_blog_sections(self):
        url_map = parse_hugo_list(self.SAMPLE_CSV)
        assert (
            url_map["content/til/2025-08-01-macos-fingerprint-reader-sudo.md"]
            == "/til/2025-08-01-macos-fingerprint-reader-sudo/"
        )

    def test_lowercases_scrap_urls(self):
        url_map = parse_hugo_list(self.SAMPLE_CSV)
        assert (
            url_map["content/scrap/2025-09-03T132628.md"] == "/scrap/2025-09-03t132628/"
        )

    def test_excludes_section_pages(self):
        url_map = parse_hugo_list(self.SAMPLE_CSV)
        assert "content/blog/_index.md" not in url_map

    def test_excludes_drafts(self):
        url_map = parse_hugo_list(self.SAMPLE_CSV)
        assert "content/blog/2025-09-12-unique-ids-when-testing.md" not in url_map

    def test_empty_input(self):
        url_map = parse_hugo_list(
            "path,slug,title,date,expiryDate,publishDate,draft,permalink,kind,section\n"
        )
        assert url_map == {}

    def test_returns_only_path_component(self):
        """Strips the scheme and host from the permalink, keeping only the path."""
        url_map = parse_hugo_list(self.SAMPLE_CSV)
        for url in url_map.values():
            assert url.startswith("/")
            assert "://" not in url


class TestScreenshotMode:
    """Test mode selection based on section membership in bannerSections."""

    def test_blog_is_template_mode(self):
        assert (
            ScreenshotMode.for_section("blog", ["blog", "crumb"])
            == ScreenshotMode.TEMPLATE
        )

    def test_crumb_is_template_mode(self):
        assert (
            ScreenshotMode.for_section("crumb", ["blog", "crumb"])
            == ScreenshotMode.TEMPLATE
        )

    def test_til_is_page_mode(self):
        assert (
            ScreenshotMode.for_section("til", ["blog", "crumb"]) == ScreenshotMode.PAGE
        )

    def test_scrap_is_page_mode(self):
        assert (
            ScreenshotMode.for_section("scrap", ["blog", "crumb"])
            == ScreenshotMode.PAGE
        )

    def test_link_is_page_mode(self):
        assert (
            ScreenshotMode.for_section("link", ["blog", "crumb"]) == ScreenshotMode.PAGE
        )

    def test_devlog_is_page_mode(self):
        assert (
            ScreenshotMode.for_section("devlog", ["blog", "crumb"])
            == ScreenshotMode.PAGE
        )

    def test_archive_is_page_mode(self):
        assert (
            ScreenshotMode.for_section("archive", ["blog", "crumb"])
            == ScreenshotMode.PAGE
        )


class TestBannerPath:
    """Test banner image path derivation from content file paths."""

    def test_uses_content_basename_as_filename(self):
        cf = ContentFile(
            path=Path("content/blog/2025-07-which-hats-are-you-wearing.md"),
            section="blog",
        )
        assert BannerPath.for_content(cf) == Path(
            "assets/img/banners/2025-07-which-hats-are-you-wearing.png"
        )

    def test_til_section(self):
        cf = ContentFile(
            path=Path("content/til/2025-08-01-macos-fingerprint-reader-sudo.md"),
            section="til",
        )
        assert BannerPath.for_content(cf) == Path(
            "assets/img/banners/2025-08-01-macos-fingerprint-reader-sudo.png"
        )

    def test_scrap_with_timestamp_name(self):
        cf = ContentFile(
            path=Path("content/scrap/2025-09-03T132628.md"),
            section="scrap",
        )
        assert BannerPath.for_content(cf) == Path(
            "assets/img/banners/2025-09-03T132628.png"
        )

    def test_output_dir_is_assets_img_banners(self):
        cf = ContentFile(
            path=Path("content/link/2025-08-10-something.md"),
            section="link",
        )
        result = BannerPath.for_content(cf)
        assert result.parent == Path("assets/img/banners")

    def test_extension_is_png(self):
        cf = ContentFile(
            path=Path("content/crumb/2025-08-12-anthropic.md"),
            section="crumb",
        )
        result = BannerPath.for_content(cf)
        assert result.suffix == ".png"


class TestShouldSkip:
    """Test filtering logic for posts that should not get generated banners."""

    def test_skip_post_with_image_field(self):
        front_matter = {"image": "/img/2025/09-pizza.jpeg"}
        assert should_skip(front_matter) is True

    def test_skip_post_with_images_array(self):
        front_matter = {"images": [{"src": "/img/photo.jpg", "alt": "A photo"}]}
        assert should_skip(front_matter) is True

    def test_skip_draft(self):
        front_matter = {"draft": True}
        assert should_skip(front_matter) is True

    def test_dont_skip_regular_post(self):
        front_matter = {"title": "Hello", "date": "2025-01-01"}
        assert should_skip(front_matter) is False

    def test_dont_skip_post_with_empty_images(self):
        front_matter = {"images": []}
        assert should_skip(front_matter) is False

    def test_dont_skip_post_with_draft_false(self):
        front_matter = {"draft": False}
        assert should_skip(front_matter) is False

    def test_skip_post_with_image_map(self):
        front_matter = {"image": {"path": "/img/photo.jpg"}}
        assert should_skip(front_matter) is True


class TestCacheLogic:
    """Test cache hit/miss determination."""

    def test_cache_hit_when_hash_matches(self):
        content_hash = "abc123"
        cache = {"assets/img/banners/my-post.png": {"content_hash": "abc123"}}
        banner_path = Path("assets/img/banners/my-post.png")
        assert check_cache(cache, banner_path, content_hash) is True

    def test_cache_miss_when_hash_differs(self):
        content_hash = "new_hash"
        cache = {"assets/img/banners/my-post.png": {"content_hash": "old_hash"}}
        banner_path = Path("assets/img/banners/my-post.png")
        assert check_cache(cache, banner_path, content_hash) is False

    def test_cache_miss_when_not_in_cache(self):
        content_hash = "abc123"
        cache = {}
        banner_path = Path("assets/img/banners/my-post.png")
        assert check_cache(cache, banner_path, content_hash) is False

    def test_cache_miss_when_banner_file_missing(self, tmp_path):
        """Even if cache says hit, if the PNG file doesn't exist, it's a miss."""
        content_hash = "abc123"
        banner_path = tmp_path / "assets/img/banners/my-post.png"
        cache = {str(banner_path): {"content_hash": "abc123"}}
        assert check_cache(cache, banner_path, content_hash, check_file=True) is False

    def test_cache_hit_when_banner_file_exists(self, tmp_path):
        """Cache hit when hash matches AND file exists."""
        banner_path = tmp_path / "assets/img/banners/my-post.png"
        banner_path.parent.mkdir(parents=True, exist_ok=True)
        banner_path.write_bytes(b"fake png")
        content_hash = "abc123"
        cache = {str(banner_path): {"content_hash": "abc123"}}
        assert check_cache(cache, banner_path, content_hash, check_file=True) is True


class TestCalculateContentHash:
    """Test content hash calculation."""

    def test_hash_is_md5_of_file_content(self, tmp_path):
        f = tmp_path / "test.md"
        content = "---\ntitle: Hello\n---\nBody text"
        f.write_text(content)
        expected = hashlib.md5(content.encode()).hexdigest()
        assert calculate_content_hash(f) == expected

    def test_different_content_gives_different_hash(self, tmp_path):
        f1 = tmp_path / "a.md"
        f2 = tmp_path / "b.md"
        f1.write_text("content a")
        f2.write_text("content b")
        assert calculate_content_hash(f1) != calculate_content_hash(f2)

    def test_same_content_gives_same_hash(self, tmp_path):
        f1 = tmp_path / "a.md"
        f2 = tmp_path / "b.md"
        f1.write_text("same content")
        f2.write_text("same content")
        assert calculate_content_hash(f1) == calculate_content_hash(f2)


class TestDiscoverSections:
    """Test section auto-discovery from filesystem."""

    def test_finds_sections_with_md_files(self, tmp_path):
        content_dir = tmp_path / "content"
        (content_dir / "blog").mkdir(parents=True)
        (content_dir / "blog" / "post.md").write_text("---\ntitle: hi\n---")
        (content_dir / "til").mkdir()
        (content_dir / "til" / "thing.md").write_text("---\ntitle: thing\n---")

        sections = discover_sections(content_dir)
        assert set(sections) == {"blog", "til"}

    def test_ignores_directories_without_md_files(self, tmp_path):
        content_dir = tmp_path / "content"
        (content_dir / "blog").mkdir(parents=True)
        (content_dir / "blog" / "post.md").write_text("content")
        (content_dir / "empty_dir").mkdir()

        sections = discover_sections(content_dir)
        assert sections == ["blog"]

    def test_ignores_non_directory_entries(self, tmp_path):
        content_dir = tmp_path / "content"
        content_dir.mkdir(parents=True)
        (content_dir / "about.md").write_text("about page")
        (content_dir / "blog").mkdir()
        (content_dir / "blog" / "post.md").write_text("content")

        sections = discover_sections(content_dir)
        assert sections == ["blog"]

    def test_ignores_index_only_sections(self, tmp_path):
        """A section with only _index.md and no regular content should not be discovered."""
        content_dir = tmp_path / "content"
        (content_dir / "empty_section").mkdir(parents=True)
        (content_dir / "empty_section" / "_index.md").write_text(
            "---\ntitle: Index\n---"
        )

        sections = discover_sections(content_dir)
        assert sections == []

    def test_sections_with_regular_content_discovered(self, tmp_path):
        content_dir = tmp_path / "content"
        (content_dir / "til").mkdir(parents=True)
        (content_dir / "til" / "_index.md").write_text("---\ntitle: TIL\n---")
        (content_dir / "til" / "2025-something.md").write_text("content")

        sections = discover_sections(content_dir)
        assert sections == ["til"]


class TestParseStagedFiles:
    """Test parsing of git diff output for --staged-only mode."""

    def test_parses_content_files(self):
        git_output = textwrap.dedent(
            """\
            content/blog/2025-07-my-post.md
            content/til/2025-08-something.md
            README.md
            script/build
        """
        )
        result = parse_staged_files(git_output)
        assert result == [
            Path("content/blog/2025-07-my-post.md"),
            Path("content/til/2025-08-something.md"),
        ]

    def test_ignores_non_content_files(self):
        git_output = "README.md\nscript/build\n"
        result = parse_staged_files(git_output)
        assert result == []

    def test_ignores_index_files(self):
        git_output = "content/blog/_index.md\ncontent/blog/real-post.md\n"
        result = parse_staged_files(git_output)
        assert result == [Path("content/blog/real-post.md")]

    def test_handles_empty_input(self):
        result = parse_staged_files("")
        assert result == []

    def test_handles_deleted_files_gracefully(self):
        """Deleted files show up in git diff but don't exist — should still be parsed."""
        git_output = "content/blog/deleted-post.md\n"
        result = parse_staged_files(git_output)
        assert result == [Path("content/blog/deleted-post.md")]
