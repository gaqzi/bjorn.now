# CLAUDE.md

## Commands
- Development: `hugo server` or `hugo server --disableFastRender`
- Production: `hugo` or `hugo --minify`

## Scripts
- ALWAYS run tests with `script/test`. Pass pytest args directly: `script/test -v --tb=short`
- Python scripts have `--help` (argparse): `all-tags.py`, `genscreenshots.py`, `lint`, `optimize-images`, `update-post-timestamps`
- `script/new --help` for content creation
- `script/fmt --help`, `script/test --help`, `script/deploy --help` for usage info
- `DEBUG=true` enables verbose output for `script/fmt` and `script/test`

## Content
- New content: `script/new --help`

### Sections
- **Blog**: Longform with explicit titles/subtitles. Navigation shows titles.
- **Crumb**: Like blog posts (titles/subtitles) but shorter.
- **TIL**: Short-form, no explicit titles. Navigation shows ~40 chars of content preview via `.Summary | plainify | truncate 40`.
- **Scrap**: Tweet-length thoughts, no titles or drafts. Minimal front matter.
- **Devlog**: Long pieces with minimal editing, showing work-in-progress. Has titles/subtitles.
- **Link**: External link posts with titles.
- **`full: true`**: Show full content in listings instead of truncating with a "more" link. For TILs and scraps that are just slightly too long for Hugo's auto-summary.

### Image Slideshows
- Add an `images` array to front matter with `src` and `alt` fields:
  ```yaml
  images:
    - src: /img/banners/my-photo.jpg
      alt: Description of the photo
  ```
- Template files: `partials/image-slideshow.html` (web) and `_default/rss.xml` (feed) — keep in sync

## Structure
- Content: `content/` (Markdown)
- Templates: `themes/sanitarium/layouts/`
- Static assets: `static/`
- CSS/JS sources: `themes/sanitarium/assets/`

## Style Guidelines
- Use native CSS nesting with `&`
- Support dark/light themes:
  - Prefer browser standard colors (like `CanvasText`) over custom CSS
  - Define theme variables in `:root` with light/dark pairs
  - Only define custom colors when browser defaults aren't sufficient
  - For SVGs and icons, use filters rather than duplicate assets

## Accessibility
- Use `:focus-visible` instead of `:focus` — prevents unwanted focus borders on mouse clicks while preserving keyboard accessibility
- Respect `prefers-reduced-motion` for animations and transitions

## Code Block Styling
- Default: centered with horizontal scroll
- `{class="full-width"}`: full-width with text wrapping — use for long text, logs, AI prompts
- `{class="no-copy-button"}`: disable auto copy button
- Classes can be combined: `{class="full-width no-copy-button"}`

## Workflow Guidelines
- Make incremental commits after each logical step
- Use descriptive commit messages
- Before committing a new post, run `script/update-post-timestamps <file>` to remove draft status and set publish time
- Test before committing
- Each commit should leave code in working state
