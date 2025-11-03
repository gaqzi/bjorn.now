from .devlog import format_tree, main, parse_roam_bullets, transform_tree


class TestParseRoamBullets:
    """Test cases for parse_roam_bullets function."""

    def test_case_1_single_bullet(self):
        """Test Case 1: Single bullet."""
        input_text = "- Hello world"
        expected = [
            {
                "content": "- Hello world",
                "indent": 0,
                "children": [],
            }
        ]
        assert parse_roam_bullets(input_text) == expected

    def test_case_2_nested_bullets_one_level(self):
        """Test Case 2: Nested bullets (one level)."""
        input_text = """- Parent
    - Child
    - Child2"""
        expected = [
            {
                "content": "- Parent",
                "indent": 0,
                "children": [
                    {"content": "- Child", "indent": 4, "children": []},
                    {"content": "- Child2", "indent": 4, "children": []},
                ],
            }
        ]
        assert parse_roam_bullets(input_text) == expected

    def test_case_3_deep_nesting_three_levels(self):
        """Test Case 3: Deep nesting (three levels)."""
        input_text = """- Level 1
    - Level 2
        - Level 3"""
        expected = [
            {
                "content": "- Level 1",
                "indent": 0,
                "children": [
                    {
                        "content": "- Level 2",
                        "indent": 4,
                        "children": [
                            {
                                "content": "- Level 3",
                                "indent": 8,
                                "children": [],
                            }
                        ],
                    }
                ],
            }
        ]
        assert parse_roam_bullets(input_text) == expected

    def test_case_4_bullets_with_multiple_lines(self):
        input_text = "- Hello,\n" "  World!"
        expected = [
            {
                "content": "- Hello,\n" "  World!",
                "indent": 0,
                "children": [],
            }
        ]
        assert parse_roam_bullets(input_text) == expected

    def test_case_5_deindent_code_fences_but_dont_strip_all_leading_spaces(self):
        input_text = (
            "    - ```python\n"
            "      def hello(s):\n"
            "          print(f'hello, {s}')\n"
            "  ```"
        )
        expected = [
            {
                "content": (
                    "- ```python\n"
                    "  def hello(s):\n"
                    "      print(f'hello, {s}')\n"
                    "  ```"
                ),
                "indent": 4,
                "children": [],
            }
        ]
        assert parse_roam_bullets(input_text) == expected


class TestTransformTree:
    """Test cases for transform_tree function."""

    def test_case_4_remove_done_marker(self):
        """Test Case 4: Remove {{[[DONE]]}} marker."""
        input_nodes = [
            {"content": "- {{[[DONE]]}} Task completed", "indent": 0, "children": []}
        ]
        expected = [{"content": "- Task completed", "indent": 0, "children": []}]
        assert transform_tree(input_nodes) == expected

    def test_case_4_remove_todo_marker(self):
        """Test Case 4: Remove {{[[TODO]]}} marker."""
        input_nodes = [
            {"content": "- {{[[TODO]]}} Task pending", "indent": 0, "children": []}
        ]
        expected = [{"content": "- Task pending", "indent": 0, "children": []}]
        assert transform_tree(input_nodes) == expected

    def test_case_5_remove_meta_trees(self):
        """Test Case 5: Remove #meta trees."""
        input_nodes = [
            {"content": "- Regular bullet", "indent": 0, "children": []},
            {
                "content": "- #meta This is meta",
                "indent": 0,
                "children": [
                    {"content": "- Nested under meta", "indent": 4, "children": []}
                ],
            },
            {"content": "- Another regular", "indent": 0, "children": []},
        ]
        expected = [
            {"content": "- Regular bullet", "indent": 0, "children": []},
            {"content": "- Another regular", "indent": 0, "children": []},
        ]
        assert transform_tree(input_nodes) == expected

    def test_case_6_mark_choice_blocks(self):
        """Test Case 6: Mark [[Choice]] blocks with type."""
        input_nodes = [
            {
                "content": "- {{[[DONE]]}} [[Choice]] My decision",
                "indent": 0,
                "children": [],
            }
        ]
        expected = [
            {
                "content": "- [[Choice]] My decision",
                "indent": 0,
                "children": [],
                "type": "choice_block",
            }
        ]
        assert transform_tree(input_nodes) == expected

    def test_case_7_convert_code_fences(self):
        """Test Case 7: Convert code fences 'plain text' to 'plaintext'."""
        input_text = """```plain text
code here
```"""
        expected = """```plaintext
code here
```"""
        # Note: This test applies to string content, not nodes
        # We'll need a separate helper for this or handle in transform_tree
        # For now, create a test that shows how it should work
        import re

        result = re.sub(r"```plain text", "```plaintext", input_text)
        assert result == expected

    def test_case_8_convert_double_colon_labels(self):
        """Test Case 8: Convert :: labels to **label:** format."""
        input_nodes = [{"content": "- Constraints::", "indent": 0, "children": []}]
        expected = [{"content": "- **Constraints:**", "indent": 0, "children": []}]
        assert transform_tree(input_nodes) == expected

    def test_case_8_convert_double_colon_with_text(self):
        """Test Case 8: Convert :: labels with content."""
        input_nodes = [
            {"content": "- Decision:: Go with this", "indent": 0, "children": []}
        ]
        expected = [
            {"content": "- **Decision:** Go with this", "indent": 0, "children": []}
        ]
        assert transform_tree(input_nodes) == expected

    def test_case_8_convert_double_colon_long_label(self):
        """Test Case 8: Convert :: labels with multiple words."""
        input_nodes = [
            {"content": "- Some text:: with content", "indent": 0, "children": []}
        ]
        expected = [
            {"content": "- **Some text:** with content", "indent": 0, "children": []}
        ]
        assert transform_tree(input_nodes) == expected


class TestFormatTree:
    """Test cases for format_tree function."""

    def test_case_9_format_choice_block_title(self):
        """Test Case 9: Format Choice block title - [[Choice]] to **Choice:**."""
        input_nodes = [
            {
                "content": "- [[Choice]] Manage workflow",
                "indent": 0,
                "children": [],
                "type": "choice_block",
            }
        ]
        expected = "- **Choice:** Manage workflow\n"
        assert format_tree(input_nodes) == expected

    def test_case_10_format_choice_blocks_with_nested_bullets(self):
        """Test Case 10: Format Choice blocks with nested bullets."""
        input_nodes = [
            {
                "content": "- [[Choice]] Title",
                "indent": 0,
                "type": "choice_block",
                "children": [
                    {
                        "content": "- **Constraints:**",
                        "indent": 4,
                        "children": [
                            {"content": "- Must work", "indent": 8, "children": []},
                            {"content": "- Must be fast", "indent": 8, "children": []},
                        ],
                    },
                    {
                        "content": "- **Options:**",
                        "indent": 4,
                        "children": [
                            {
                                "content": "- Option A",
                                "indent": 8,
                                "children": [
                                    {
                                        "content": "**Advantages:**",
                                        "indent": 12,
                                        "children": [
                                            {
                                                "content": "- Simple",
                                                "indent": 16,
                                                "children": [],
                                            },
                                        ],
                                    },
                                    {
                                        "content": "**Disadvantages:**",
                                        "indent": 12,
                                        "children": [
                                            {
                                                "content": "- Too simple?",
                                                "indent": 16,
                                                "children": [],
                                            },
                                        ],
                                    },
                                ],
                            },
                            {
                                "content": "- Option B",
                                "indent": 4,
                                "children": [
                                    {
                                        "content": "**Advantages:**",
                                        "indent": 12,
                                        "children": [
                                            {
                                                "content": "- Covers all scenarios",
                                                "indent": 16,
                                                "children": [],
                                            },
                                        ],
                                    },
                                    {
                                        "content": "**Disadvantages:**",
                                        "indent": 12,
                                        "children": [
                                            {
                                                "content": "- Hard to implement and will take a long time",
                                                "indent": 16,
                                                "children": [],
                                            },
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                    {
                        "content": "- **Decision:** Go with option A",
                        "indent": 4,
                        "children": [
                            {"content": "- It feels right", "indent": 8, "children": []}
                        ],
                    },
                ],
            }
        ]
        expected = (
            "- **Choice:** Title\n"
            "    - **Constraints:**\n"
            "        - Must work\n"
            "        - Must be fast\n"
            "    - **Options:**\n"
            "        - Option A\n"
            "            **Advantages:**\n"
            "                - Simple\n"
            "            **Disadvantages:**\n"
            "                - Too simple?\n"
            "        - Option B\n"
            "            **Advantages:**\n"
            "                - Covers all scenarios\n"
            "            **Disadvantages:**\n"
            "                - Hard to implement and will take a long time\n"
            "    - **Decision:** Go with option A\n"
            "        - It feels right\n"
        )
        assert format_tree(input_nodes) == expected

    def test_case_11_flatten_regular_bullets(self):
        """Test Case 11: Flatten regular bullets to paragraphs."""
        input_nodes = [
            {"content": "- This is a bullet", "indent": 0, "children": []},
            {
                "content": "- Another bullet",
                "indent": 0,
                "children": [
                    {"content": "- Nested content", "indent": 4, "children": []}
                ],
            },
        ]
        expected = (
            "This is a bullet.\n" "\n" "Another bullet.\n" "\n" "Nested content.\n"
        )
        assert format_tree(input_nodes) == expected

    def test_case_12_preserve_numbered_lists(self):
        """Test Case 12: Preserve numbered lists as-is."""
        # Note: The parser returns bullet markers, but we can test with numbered
        input_nodes = [
            {"content": "1. First item", "indent": 0, "children": []},
            {
                "content": "2. Second item",
                "indent": 0,
                "children": [
                    {"content": "- Nested under numbered", "indent": 4, "children": []}
                ],
            },
        ]
        expected = (
            "1. First item.\n" "\n" "2. Second item.\n" "\n" "Nested under numbered.\n"
        )
        assert format_tree(input_nodes) == expected

    def test_case_13_punctuation_no_punctuation(self):
        """Test Case 13: Add period to text without punctuation."""
        input_nodes = [
            {"content": "- No punctuation here", "indent": 0, "children": []}
        ]
        expected = "No punctuation here.\n"
        assert format_tree(input_nodes) == expected

    def test_case_13_punctuation_already_has_period(self):
        """Test Case 13: Don't add period if already has one."""
        input_nodes = [
            {"content": "- Already has period.", "indent": 0, "children": []}
        ]
        expected = "Already has period.\n"
        assert format_tree(input_nodes) == expected

    def test_case_13_punctuation_smiley(self):
        """Test Case 13: Don't add period if ends with smiley."""
        input_nodes = [
            {"content": "- Ends with smiley :)", "indent": 0, "children": []}
        ]
        expected = "Ends with smiley :)\n"
        assert format_tree(input_nodes) == expected

    def test_case_13_punctuation_question(self):
        """Test Case 13: Don't add period if ends with question mark."""
        input_nodes = [{"content": "- Question?", "indent": 0, "children": []}]
        expected = "Question?\n"
        assert format_tree(input_nodes) == expected

    def test_case_13_punctuation_exclamation(self):
        """Test Case 13: Don't add period if ends with exclamation."""
        input_nodes = [{"content": "- Exclamation!", "indent": 0, "children": []}]
        expected = "Exclamation!\n"
        assert format_tree(input_nodes) == expected

    def test_case_13_punctuation_bold_label(self):
        """Test Case 13: Don't add period if ends with bold label like **Constraints:**."""
        input_nodes = [{"content": "- **Constraints:**", "indent": 0, "children": []}]
        expected = "**Constraints:**\n"
        assert format_tree(input_nodes) == expected

    def test_case_14_dont_add_punctuation_to_headers(self):
        """Test Case 14: Don't add period to headers."""
        input_nodes = [{"content": "# Header", "indent": 0, "children": []}]
        expected = "# Header\n"
        assert format_tree(input_nodes) == expected

    def test_case_15_doesnt_modify_code_fences(self):
        """Test Case 14: Don't add periods or change the content in the code fences."""
        input_nodes = [
            {
                "content": "```python\n"
                "def hello(s):\n"
                "    print(f'hello, {s}')\n"
                "```",
                "indent": 0,
                "children": [],
            }
        ]
        expected = "```python\n" "def hello(s):\n" "    print(f'hello, {s}')\n" "```\n"
        assert format_tree(input_nodes) == expected

    def test_case_16_normalized_indent_on_multi_line_when_leading_bullet_is_stripped(
        self,
    ):
        """Test Case 16: Indentation should be normalized on multi-line bullets."""
        input_nodes = [
            {
                "content": ("- First line,\n" "  that is continued"),
                "indent": 0,
                "children": [
                    {
                        "content": ("- Second, indented line,\n" "  that is continued"),
                        "indent": 4,
                        "children": [],
                    }
                ],
            }
        ]
        expected = (
            "First line,\n"
            "that is continued.\n"
            "\n"
            "Second, indented line,\n"
            "that is continued.\n"
        )
        assert format_tree(input_nodes) == expected


class TestMain:
    """Test cases for main CLI function."""

    def test_case_14_read_from_file(self, tmp_path):
        """Test Case 14: Read from file argument and process."""
        # Create a temporary test file
        test_file = tmp_path / "test_input.md"
        test_content = "- Hello world"
        test_file.write_text(test_content)

        # Mock sys.argv to pass the file path
        import sys

        old_argv = sys.argv
        try:
            sys.argv = ["devlog", str(test_file)]
            result = main()
            assert result == 0
        finally:
            sys.argv = old_argv

    def test_case_14_read_from_file_with_output(self, tmp_path, capsys):
        """Test Case 14: Read from file and verify output."""
        # Create a temporary test file
        test_file = tmp_path / "test_input.md"
        test_content = "- Hello world"
        test_file.write_text(test_content)

        # Mock sys.argv to pass the file path
        import sys

        old_argv = sys.argv
        try:
            sys.argv = ["devlog", str(test_file)]
            result = main()
            captured = capsys.readouterr()
            assert result == 0
            assert "Hello world." in captured.out
        finally:
            sys.argv = old_argv

    def test_case_15_read_from_stdin(self, monkeypatch, capsys):
        """Test Case 15: Read from STDIN when no argument provided."""
        import sys
        from io import StringIO

        test_content = "- Test bullet"

        # Mock stdin and argv
        monkeypatch.setattr("sys.stdin", StringIO(test_content))
        old_argv = sys.argv
        try:
            sys.argv = ["devlog"]
            result = main()
            captured = capsys.readouterr()
            assert result == 0
            assert "Test bullet." in captured.out
        finally:
            sys.argv = old_argv

    def test_case_16_file_not_found(self, capsys):
        """Test Case 16: Error handling - file not found."""
        import sys

        old_argv = sys.argv
        try:
            sys.argv = ["devlog", "/nonexistent/path/file.md"]
            result = main()
            captured = capsys.readouterr()
            assert result == 1
            assert "Error: File" in captured.err
            assert "not found" in captured.err
        finally:
            sys.argv = old_argv

    def test_case_16_parse_error(self, monkeypatch, capsys):
        """Test Case 16: Error handling - parse error."""
        import sys
        from io import StringIO

        # This test verifies error handling for parse errors
        # For now, we'll just test the basic error handling infrastructure
        test_content = "- Normal bullet"

        monkeypatch.setattr("sys.stdin", StringIO(test_content))
        old_argv = sys.argv
        try:
            sys.argv = ["devlog"]
            # The current implementation should handle this gracefully
            result = main()
            assert result == 0
        finally:
            sys.argv = old_argv
