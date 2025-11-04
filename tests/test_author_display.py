import pytest


class TestAuthorDisplay:
    """Test suite for author display functionality."""

    def test_individual_post_shows_author_information(
        self, hugo_site, get_post_html_fixture
    ):
        """Test that individual posts show complete author information (hideAuthor: false).

        Verifies:
        - Author avatar display with correct attributes
        - Author name links
        - Meta content structure
        - Link consistency between avatar and text
        - Accessibility support (alt text)
        - Author metadata consistency across meta tags
        """
        soup = get_post_html_fixture("blog/2025/07/12/which-hat-are-you-wearing")

        author_avatar = soup.find("img", class_="author-avatar")
        assert author_avatar is not None, "Individual post should display author avatar"

        expected_src = (
            "/authors/bj%C3%B6rn-2_hu_61196dca2776a203.jpg"  # URL-encoded björn
        )
        assert (
            author_avatar.get("src") == expected_src
        ), f"Avatar src should be '{expected_src}' but was '{author_avatar.get('src')}'"
        assert (
            author_avatar.get("alt") == "Björn Andersson"
        ), f"Avatar alt should be 'Björn Andersson' but was '{author_avatar.get('alt')}'"
        assert author_avatar.get("width") == "40", "Avatar should have width='40'"
        assert author_avatar.get("height") == "40", "Avatar should have height='40'"

        alt_text = author_avatar.get("alt")
        assert alt_text is not None, "Author avatar should have alt text"
        assert len(alt_text.strip()) > 0, "Alt text should not be empty"
        assert "Björn Andersson" in alt_text, "Alt text should contain author name"

        # Test author name links
        author_links = soup.find_all("a", class_="author")
        assert len(author_links) >= 1, "Individual post should have author link(s)"

        # Find the text author link (not just the avatar link)
        text_author_link = None
        for link in author_links:
            if link.get_text().strip() == "Björn Andersson":
                text_author_link = link
                break

        assert (
            text_author_link is not None
        ), "Should find author name link with 'Björn Andersson'"
        assert (
            text_author_link.get("href") == "/about/"
        ), f"Author link should go to '/about/' but was '{text_author_link.get('href')}'"

        urls = [link.get("href") for link in author_links]
        unique_urls = set(urls)
        assert (
            len(unique_urls) == 1
        ), f"All author links should point to same URL, but found: {unique_urls}"
        assert (
            urls[0] == "/about/"
        ), f"Author links should point to '/about/' but pointed to '{urls[0]}'"

        meta_div = soup.find("div", class_="meta")
        assert meta_div is not None, "Should have meta div"

        meta_content = meta_div.find("div", class_="meta-content")
        assert meta_content is not None, "Should have meta-content div"

        meta_lines = meta_content.find_all("div", class_="meta-line")
        assert len(meta_lines) >= 1, "Should have at least one meta-line div"

        first_meta_line = meta_lines[0]
        author_link = first_meta_line.find("a", class_="author")
        assert author_link is not None, "First meta-line should contain author link"

        meta_author = soup.find("meta", attrs={"name": "author"})
        assert meta_author is not None, "Should have meta author tag"
        assert (
            meta_author.get("content") == "Björn Andersson"
        ), f"Meta author should be 'Björn Andersson' but was '{meta_author.get('content')}'"

        twitter_author = soup.find("meta", attrs={"name": "twitter:data1"})
        if twitter_author:
            assert (
                twitter_author.get("content") == "Björn Andersson"
            ), f"Twitter author should be 'Björn Andersson' but was '{twitter_author.get('content')}'"

        visible_author = None
        for link in author_links:
            text = link.get_text().strip()
            if text == "Björn Andersson":
                visible_author = text
                break

        assert (
            visible_author == "Björn Andersson"
        ), "Visible author should match meta author"

    @pytest.mark.parametrize(
        "page_path,page_name",
        [
            ("index.html", "homepage"),
            ("blog/index.html", "blog listing"),
            ("tags/how-to/index.html", "how-to tag page"),
        ],
    )
    def test_listing_pages_hide_author_information(
        self, hugo_site, parse_html_fixture, page_path, page_name
    ):
        """Test that listing pages hide author information (hideAuthor: true).

        Tests homepage, blog listing, and tag pages to ensure no author
        avatars or names are displayed in post listings.
        """
        page_file = hugo_site / page_path

        if not page_file.exists():
            pytest.fail(f"Page {page_path} does not exist")

        soup = parse_html_fixture(page_file)

        author_avatars = soup.find_all("img", class_="author-avatar")
        assert (
            len(author_avatars) == 0
        ), f"{page_name.title()} should hide author avatars but found {len(author_avatars)}"

        author_links = soup.find_all("a", class_="author")
        assert (
            len(author_links) == 0
        ), f"{page_name.title()} should hide author names but found {len(author_links)}"
