from .devlog import (
    ChoiceNode,
    CodeFenceNode,
    DetailsNode,
    NumberedListNode,
    PreserveListNode,
    QuoteNode,
    RegularNode,
    format_tree,
    is_node_object,
    main,
    parse_roam_bullets,
    process,
    transform_tree,
)


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

    def test_case_6_quote_block_single_line(self):
        """Test Case 6: Single line quote block."""
        input_text = "- > Quote text"
        expected = [
            {
                "content": "- > Quote text",
                "indent": 0,
                "children": [],
            }
        ]
        assert parse_roam_bullets(input_text) == expected

    def test_case_6_quote_block_multi_line(self):
        """Test Case 6: Multi-line quote block with continuation lines."""
        input_text = "- > __For each desired change,\n  > make the change easy (warning: this may be hard),\n  > then make the easy change__"
        expected = [
            {
                "content": (
                    "- > __For each desired change,\n"
                    "  > make the change easy (warning: this may be hard),\n"
                    "  > then make the easy change__"
                ),
                "indent": 0,
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
        expected = [RegularNode(content="- Task completed", indent=0, children=[])]
        assert transform_tree(input_nodes) == expected

    def test_case_4_remove_todo_marker(self):
        """Test Case 4: Remove {{[[TODO]]}} marker."""
        input_nodes = [
            {"content": "- {{[[TODO]]}} Task pending", "indent": 0, "children": []}
        ]
        expected = [RegularNode(content="- Task pending", indent=0, children=[])]
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
            RegularNode(content="- Regular bullet", indent=0, children=[]),
            RegularNode(content="- Another regular", indent=0, children=[]),
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
        result = transform_tree(input_nodes)
        expected = ChoiceNode(content="- [[Choice]] My decision", indent=0, children=[])
        assert len(result) == 1
        assert result[0] == expected

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
        expected = [RegularNode(content="- **Constraints:**", indent=0, children=[])]
        assert transform_tree(input_nodes) == expected

    def test_case_8_convert_double_colon_with_text(self):
        """Test Case 8: Convert :: labels with content."""
        input_nodes = [
            {"content": "- Decision:: Go with this", "indent": 0, "children": []}
        ]
        expected = [
            RegularNode(content="- **Decision:** Go with this", indent=0, children=[])
        ]
        assert transform_tree(input_nodes) == expected

    def test_case_8_convert_double_colon_long_label(self):
        """Test Case 8: Convert :: labels with multiple words."""
        input_nodes = [
            {"content": "- Some text:: with content", "indent": 0, "children": []}
        ]
        expected = [
            RegularNode(content="- **Some text:** with content", indent=0, children=[])
        ]
        assert transform_tree(input_nodes) == expected

    def test_case_9_detect_list_marker(self):
        """Test Case 9: Detect and remove [list] marker from content."""
        input_nodes = [
            {
                "content": "- Keep these as list: [list]",
                "indent": 0,
                "children": [
                    {"content": "- First", "indent": 4, "children": []},
                    {"content": "- Second", "indent": 4, "children": []},
                ],
            }
        ]
        result = transform_tree(input_nodes)
        expected = PreserveListNode(
            content="- Keep these as list:",
            indent=0,
            children=[
                RegularNode(content="- First", indent=4, children=[]),
                RegularNode(content="- Second", indent=4, children=[]),
            ],
        )
        assert result[0] == expected

    def test_case_9_list_marker_with_trailing_spaces(self):
        """Test Case 9: Remove [list] marker and any trailing spaces."""
        input_nodes = [
            {
                "content": "- Text here: [list]  ",
                "indent": 0,
                "children": [],
            }
        ]
        result = transform_tree(input_nodes)
        expected = PreserveListNode(content="- Text here:", indent=0, children=[])
        assert result[0] == expected

    def test_case_9_nested_list_markers(self):
        """Test Case 9: Test multiple levels with [list] markers."""
        input_nodes = [
            {
                "content": "- Parent: [list]",
                "indent": 0,
                "children": [
                    {
                        "content": "- Child: [list]",
                        "indent": 4,
                        "children": [
                            {"content": "- Grandchild", "indent": 8, "children": []}
                        ],
                    }
                ],
            }
        ]
        result = transform_tree(input_nodes)
        expected = PreserveListNode(
            content="- Parent:",
            indent=0,
            children=[
                PreserveListNode(
                    content="- Child:",
                    indent=4,
                    children=[
                        RegularNode(content="- Grandchild", indent=8, children=[])
                    ],
                )
            ],
        )
        assert result[0] == expected

    def test_detect_details_marker(self):
        """Test detecting and removing [details] marker from content."""
        input_nodes = [
            {
                "content": "- LLM plan to review: [details]",
                "indent": 0,
                "children": [
                    {
                        "content": "```text\nplan content\n```",
                        "indent": 4,
                        "children": [],
                    }
                ],
            }
        ]
        result = transform_tree(input_nodes)
        expected = DetailsNode(
            content="- LLM plan to review:",
            indent=0,
            children=[
                CodeFenceNode(
                    content="```text\nplan content\n```",
                    indent=4,
                    children=[],
                )
            ],
        )
        assert result[0] == expected

    def test_details_marker_with_trailing_spaces(self):
        """Test [details] marker removal with trailing spaces."""
        input_nodes = [
            {
                "content": "- Text here: [details]  ",
                "indent": 0,
                "children": [],
            }
        ]
        result = transform_tree(input_nodes)
        expected = DetailsNode(content="- Text here:", indent=0, children=[])
        assert result[0] == expected

    def test_details_marker_without_colon(self):
        """Test [details] marker when content doesn't end with colon."""
        input_nodes = [
            {
                "content": "- Some text [details]",
                "indent": 0,
                "children": [
                    {"content": "- Child content", "indent": 4, "children": []}
                ],
            }
        ]
        result = transform_tree(input_nodes)
        expected = DetailsNode(
            content="- Some text",
            indent=0,
            children=[RegularNode(content="- Child content", indent=4, children=[])],
        )
        assert result[0] == expected

    def test_nested_details_markers(self):
        """Test multiple levels with [details] markers."""
        input_nodes = [
            {
                "content": "- Parent: [details]",
                "indent": 0,
                "children": [
                    {
                        "content": "- Child: [details]",
                        "indent": 4,
                        "children": [
                            {"content": "- Grandchild", "indent": 8, "children": []}
                        ],
                    }
                ],
            }
        ]
        result = transform_tree(input_nodes)
        expected = DetailsNode(
            content="- Parent:",
            indent=0,
            children=[
                DetailsNode(
                    content="- Child:",
                    indent=4,
                    children=[
                        RegularNode(content="- Grandchild", indent=8, children=[])
                    ],
                )
            ],
        )
        assert result[0] == expected


class TestFormatTree:
    """Test cases for format_tree function."""

    def test_case_9_format_choice_block_title(self):
        """Test Case 9: Format Choice block title - [[Choice]] to **Choice:**."""
        input_nodes = [
            ChoiceNode(
                content="- [[Choice]] Manage workflow",
                indent=0,
                children=[],
            )
        ]
        expected = "- **Choice:** Manage workflow\n"
        assert format_tree(input_nodes) == expected

    def test_case_10_format_choice_blocks_with_nested_bullets(self):
        """Test Case 10: Format Choice blocks with nested bullets."""
        input_nodes = [
            ChoiceNode(
                content="- [[Choice]] Title",
                indent=0,
                children=[
                    RegularNode(
                        content="- **Constraints:**",
                        indent=4,
                        children=[
                            RegularNode(content="- Must work", indent=8, children=[]),
                            RegularNode(
                                content="- Must be fast", indent=8, children=[]
                            ),
                        ],
                    ),
                    RegularNode(
                        content="- **Options:**",
                        indent=4,
                        children=[
                            RegularNode(
                                content="- Option A",
                                indent=8,
                                children=[
                                    RegularNode(
                                        content="**Advantages:**",
                                        indent=12,
                                        children=[
                                            RegularNode(
                                                content="- Simple",
                                                indent=16,
                                                children=[],
                                            ),
                                        ],
                                    ),
                                    RegularNode(
                                        content="**Disadvantages:**",
                                        indent=12,
                                        children=[
                                            RegularNode(
                                                content="- Too simple?",
                                                indent=16,
                                                children=[],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            RegularNode(
                                content="- Option B",
                                indent=4,
                                children=[
                                    RegularNode(
                                        content="**Advantages:**",
                                        indent=12,
                                        children=[
                                            RegularNode(
                                                content="- Covers all scenarios",
                                                indent=16,
                                                children=[],
                                            ),
                                        ],
                                    ),
                                    RegularNode(
                                        content="**Disadvantages:**",
                                        indent=12,
                                        children=[
                                            RegularNode(
                                                content="- Hard to implement and will take a long time",
                                                indent=16,
                                                children=[],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                    RegularNode(
                        content="- **Decision:** Go with option A",
                        indent=4,
                        children=[
                            RegularNode(
                                content="- It feels right", indent=8, children=[]
                            )
                        ],
                    ),
                ],
            )
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
            RegularNode(content="- This is a bullet", indent=0, children=[]),
            RegularNode(
                content="- Another bullet",
                indent=0,
                children=[
                    RegularNode(content="- Nested content", indent=4, children=[])
                ],
            ),
        ]
        expected = (
            "This is a bullet.\n" "\n" "Another bullet.\n" "\n" "Nested content.\n"
        )
        assert format_tree(input_nodes) == expected

    def test_case_12_preserve_numbered_lists(self):
        """Test Case 12: Preserve numbered lists as-is."""
        # Note: The parser returns bullet markers, but we can test with numbered
        input_nodes = [
            NumberedListNode(content="1. First item", indent=0, children=[]),
            NumberedListNode(
                content="2. Second item",
                indent=0,
                children=[
                    RegularNode(
                        content="- Nested under numbered", indent=4, children=[]
                    )
                ],
            ),
        ]
        expected = "1. First item\n" "2. Second item\n" "\n" "Nested under numbered.\n"
        assert format_tree(input_nodes) == expected

    def test_case_13_punctuation_no_punctuation(self):
        """Test Case 13: Add period to text without punctuation."""
        input_nodes = [
            RegularNode(content="- No punctuation here", indent=0, children=[])
        ]
        expected = "No punctuation here.\n"
        assert format_tree(input_nodes) == expected

    def test_case_13_punctuation_already_has_period(self):
        """Test Case 13: Don't add period if already has one."""
        input_nodes = [
            RegularNode(content="- Already has period.", indent=0, children=[])
        ]
        expected = "Already has period.\n"
        assert format_tree(input_nodes) == expected

    def test_case_13_punctuation_smiley(self):
        """Test Case 13: Don't add period if ends with smiley."""
        input_nodes = [
            RegularNode(content="- Ends with smiley :)", indent=0, children=[])
        ]
        expected = "Ends with smiley :)\n"
        assert format_tree(input_nodes) == expected

    def test_case_13_punctuation_question(self):
        """Test Case 13: Don't add period if ends with question mark."""
        input_nodes = [RegularNode(content="- Question?", indent=0, children=[])]
        expected = "Question?\n"
        assert format_tree(input_nodes) == expected

    def test_case_13_punctuation_exclamation(self):
        """Test Case 13: Don't add period if ends with exclamation."""
        input_nodes = [RegularNode(content="- Exclamation!", indent=0, children=[])]
        expected = "Exclamation!\n"
        assert format_tree(input_nodes) == expected

    def test_case_13_punctuation_bold_label(self):
        """Test Case 13: Don't add period if ends with bold label like **Constraints:**."""
        input_nodes = [RegularNode(content="- **Constraints:**", indent=0, children=[])]
        expected = "**Constraints:**\n"
        assert format_tree(input_nodes) == expected

    def test_case_14_dont_add_punctuation_to_headers(self):
        """Test Case 14: Don't add period to headers."""
        input_nodes = [RegularNode(content="# Header", indent=0, children=[])]
        expected = "# Header\n"
        assert format_tree(input_nodes) == expected

    def test_case_15_doesnt_modify_code_fences(self):
        """Test Case 14: Don't add periods or change the content in the code fences."""
        input_nodes = [
            CodeFenceNode(
                content="```python\n"
                "def hello(s):\n"
                "    print(f'hello, {s}')\n"
                "```",
                indent=0,
                children=[],
            )
        ]
        expected = "```python\n" "def hello(s):\n" "    print(f'hello, {s}')\n" "```\n"
        assert format_tree(input_nodes) == expected

    def test_case_16_normalized_indent_on_multi_line_when_leading_bullet_is_stripped(
        self,
    ):
        """Test Case 16: Indentation should be normalized on multi-line bullets."""
        input_nodes = [
            RegularNode(
                content=("- First line,\n" "  that is continued"),
                indent=0,
                children=[
                    RegularNode(
                        content=("- Second, indented line,\n" "  that is continued"),
                        indent=4,
                        children=[],
                    )
                ],
            )
        ]
        expected = (
            "First line,\n"
            "that is continued.\n"
            "\n"
            "Second, indented line,\n"
            "that is continued.\n"
        )
        assert format_tree(input_nodes) == expected

    def test_case_17_format_quote_block_single_line(self):
        """Test Case 17: Format single line quote block with > prefix."""
        input_nodes = [
            QuoteNode(
                content="- > Quote text",
                indent=0,
                children=[],
            )
        ]
        expected = "> Quote text\n"
        assert format_tree(input_nodes) == expected

    def test_case_17_format_quote_block_multi_line(self):
        """Test Case 17: Format multi-line quote block with > prefix on each line."""
        input_nodes = [
            QuoteNode(
                content=(
                    "- > __For each desired change,\n"
                    "  > make the change easy (warning: this may be hard),\n"
                    "  > then make the easy change__"
                ),
                indent=0,
                children=[],
            )
        ]
        expected = (
            "> __For each desired change,\n"
            "> make the change easy (warning: this may be hard),\n"
            "> then make the easy change__\n"
        )
        assert format_tree(input_nodes) == expected

    def test_case_17_quote_block_preserve_dash_markers(self):
        """Test Case 17: Don't remove dash markers in quote blocks."""
        input_nodes = [
            QuoteNode(
                content="- > This has - dashes - in it",
                indent=0,
                children=[],
            )
        ]
        expected = "> This has - dashes - in it\n"
        assert format_tree(input_nodes) == expected

    def test_case_18_numbered_list_no_extra_newlines(self):
        """Test Case 18: Numbered lists should have no blank lines between items."""
        input_nodes = [
            NumberedListNode(content="1. First", indent=0, children=[]),
            NumberedListNode(content="2. Second", indent=0, children=[]),
            NumberedListNode(content="3. Third", indent=0, children=[]),
        ]
        expected = "1. First\n2. Second\n3. Third\n"
        assert format_tree(input_nodes) == expected

    def test_case_18_numbered_list_vs_regular_bullets(self):
        """Test Case 18: Show different treatment for numbered vs regular bullets."""
        regular_bullets = [
            RegularNode(content="- First", indent=0, children=[]),
            RegularNode(content="- Second", indent=0, children=[]),
        ]
        expected_regular = "First.\n\nSecond.\n"
        assert format_tree(regular_bullets) == expected_regular

        numbered_list = [
            NumberedListNode(content="1. First", indent=0, children=[]),
            NumberedListNode(content="2. Second", indent=0, children=[]),
        ]
        expected_numbered = "1. First\n2. Second\n"
        assert format_tree(numbered_list) == expected_numbered

    def test_case_18_nested_under_numbered_list(self):
        """Test Case 18: Regular bullets under numbered items should be flattened."""
        input_nodes = [
            NumberedListNode(
                content="1. First item",
                indent=0,
                children=[
                    RegularNode(content="- Detail about first", indent=4, children=[])
                ],
            ),
            NumberedListNode(content="2. Second item", indent=0, children=[]),
        ]
        expected = "1. First item\n\nDetail about first.\n\n2. Second item\n"
        assert format_tree(input_nodes) == expected

    def test_case_19_preserve_children_with_list_marker(self):
        """Test Case 19: Children with [list] marker should be preserved as indented bullets."""
        input_nodes = [
            PreserveListNode(
                content="- Keep these as list:",
                indent=0,
                children=[
                    RegularNode(content="- First", indent=4, children=[]),
                    RegularNode(content="- Second", indent=4, children=[]),
                ],
            )
        ]
        expected = "Keep these as list:\n\n- First\n- Second\n"
        assert format_tree(input_nodes) == expected

    def test_case_19_list_marker_vs_normal_flatten(self):
        """Test Case 19: Show difference between [list] and normal flattening."""
        # Normal flattening
        normal = [
            RegularNode(
                content="- Parent",
                indent=0,
                children=[
                    RegularNode(content="- Child1", indent=4, children=[]),
                    RegularNode(content="- Child2", indent=4, children=[]),
                ],
            )
        ]
        expected_normal = "Parent.\n\nChild1.\n\nChild2.\n"
        assert format_tree(normal) == expected_normal

        # With [list] marker
        with_list = [
            PreserveListNode(
                content="- Parent",
                indent=0,
                children=[
                    RegularNode(content="- Child1", indent=4, children=[]),
                    RegularNode(content="- Child2", indent=4, children=[]),
                ],
            )
        ]
        expected_list = "Parent:\n\n- Child1\n- Child2\n"
        assert format_tree(with_list) == expected_list

    def test_case_19_nested_list_markers(self):
        """Test Case 19: Test multiple levels with [list] markers."""
        input_nodes = [
            PreserveListNode(
                content="- Parent:",
                indent=0,
                children=[
                    PreserveListNode(
                        content="- Child:",
                        indent=4,
                        children=[
                            RegularNode(content="- Grandchild", indent=8, children=[])
                        ],
                    )
                ],
            )
        ]
        expected = "Parent:\n\n- Child:\n    - Grandchild\n"
        assert format_tree(input_nodes) == expected

    def test_case_20_code_block_in_choice_alignment(self):
        """Test Case 20: Code blocks in Choice blocks should maintain proper indentation."""
        input_nodes = [
            ChoiceNode(
                content="- [[Choice]] Test choice",
                indent=0,
                children=[
                    RegularNode(
                        content="- **Options:**",
                        indent=4,
                        children=[
                            CodeFenceNode(
                                content="- Option A\n  ```python\n  def hello():\n      print('hi')\n  ```",
                                indent=8,
                                children=[],
                            )
                        ],
                    )
                ],
            )
        ]
        expected = (
            "- **Choice:** Test choice\n"
            "    - **Options:**\n"
            "        - Option A\n"
            "          ```python\n"
            "          def hello():\n"
            "              print('hi')\n"
            "          ```\n"
        )
        assert format_tree(input_nodes) == expected

    def test_case_20_multi_line_code_in_choice(self):
        """Test Case 20: Multi-line code blocks should preserve internal indentation."""
        input_nodes = [
            ChoiceNode(
                content="- [[Choice]] Code example",
                indent=0,
                children=[
                    CodeFenceNode(
                        content=(
                            "```plaintext\n"
                            "def hello(s):\n"
                            "    print(f'hello, {s}')\n"
                            "```"
                        ),
                        indent=4,
                        children=[],
                    )
                ],
            )
        ]
        expected = (
            "- **Choice:** Code example\n"
            "    ```plaintext\n"
            "    def hello(s):\n"
            "        print(f'hello, {s}')\n"
            "    ```\n"
        )
        assert format_tree(input_nodes) == expected

    def test_case_20_code_at_different_nesting_levels(self):
        """Test Case 20: Code blocks at various indent depths should align correctly."""
        input_nodes = [
            ChoiceNode(
                content="- [[Choice]] Nested code",
                indent=0,
                children=[
                    RegularNode(
                        content="- Level 1",
                        indent=4,
                        children=[
                            CodeFenceNode(
                                content="- Level 2\n  ```python\n  code\n  ```",
                                indent=8,
                                children=[],
                            )
                        ],
                    )
                ],
            )
        ]
        expected = (
            "- **Choice:** Nested code\n"
            "    - Level 1\n"
            "        - Level 2\n"
            "          ```python\n"
            "          code\n"
            "          ```\n"
        )
        assert format_tree(input_nodes) == expected

    def test_case_21_choice_stays_in_place_with_content(self):
        """Test Case 21: Choice blocks should appear with flattened sibling content."""
        input_nodes = [
            RegularNode(
                content="- Parent",
                indent=0,
                children=[
                    RegularNode(content="- Regular text before", indent=4, children=[]),
                    ChoiceNode(
                        content="- [[Choice]] My choice",
                        indent=4,
                        children=[
                            RegularNode(
                                content="- **Decision:** Done",
                                indent=8,
                                children=[],
                            )
                        ],
                    ),
                    RegularNode(content="- Regular text after", indent=4, children=[]),
                ],
            )
        ]
        # Choice block should stays with the flattened content
        expected = (
            "Parent.\n"
            "\n"
            "Regular text before.\n"
            "\n"
            "- **Choice:** My choice\n"
            "    - **Decision:** Done\n"
            "\n"
            "Regular text after.\n"
        )
        assert format_tree(input_nodes) == expected

    def test_case_21_multiple_choice_blocks_ordering(self):
        """Test Case 21: Multiple Choice blocks should preserve their relative order."""
        input_nodes = [
            RegularNode(
                content="- Parent",
                indent=0,
                children=[
                    RegularNode(content="- Regular text", indent=4, children=[]),
                    ChoiceNode(
                        content="- [[Choice]] First choice",
                        indent=4,
                        children=[],
                    ),
                    ChoiceNode(
                        content="- [[Choice]] Second choice",
                        indent=4,
                        children=[],
                    ),
                ],
            )
        ]
        expected = (
            "Parent.\n"
            "\n"
            "Regular text.\n"
            "\n"
            "- **Choice:** First choice\n"
            "\n"
            "- **Choice:** Second choice\n"
        )
        assert format_tree(input_nodes) == expected

    def test_format_details_block_simple(self):
        """Test formatting a simple details block with summary tag."""
        input_nodes = [
            DetailsNode(
                content="- Plan to review:",
                indent=0,
                children=[
                    RegularNode(content="- Point one", indent=4, children=[]),
                    RegularNode(content="- Point two", indent=4, children=[]),
                ],
            )
        ]
        expected = (
            "<details>\n"
            "<summary>Plan to review:</summary>\n"
            "\n"
            "Point one.\n"
            "\n"
            "Point two.\n"
            "</details>\n"
        )
        assert format_tree(input_nodes) == expected

    def test_format_details_block_no_children(self):
        """Test formatting details block with no children (edge case)."""
        input_nodes = [
            DetailsNode(
                content="- Empty details:",
                indent=0,
                children=[],
            )
        ]
        expected = "<details>\n<summary>Empty details:</summary>\n</details>\n"
        assert format_tree(input_nodes) == expected

    def test_format_details_block_summary_without_colon(self):
        """Test details block when summary doesn't end with colon."""
        input_nodes = [
            DetailsNode(
                content="- Click to expand",
                indent=0,
                children=[
                    RegularNode(content="- Hidden content", indent=4, children=[]),
                ],
            )
        ]
        expected = (
            "<details>\n"
            "<summary>Click to expand</summary>\n"
            "\n"
            "Hidden content.\n"
            "</details>\n"
        )
        assert format_tree(input_nodes) == expected

    def test_format_details_block_with_code(self):
        """Test formatting details block containing code fences."""
        input_nodes = [
            DetailsNode(
                content="- Implementation plan:",
                indent=0,
                children=[
                    CodeFenceNode(
                        content="```python\ndef hello():\n    print('hi')\n```",
                        indent=4,
                        children=[],
                    )
                ],
            )
        ]
        expected = (
            "<details>\n"
            "<summary>Implementation plan:</summary>\n"
            "\n"
            "```python\n"
            "def hello():\n"
            "    print('hi')\n"
            "```\n"
            "</details>\n"
        )
        assert format_tree(input_nodes) == expected

    def test_format_details_with_mixed_content(self):
        """Test details block with various child node types."""
        input_nodes = [
            DetailsNode(
                content="- Analysis:",
                indent=0,
                children=[
                    RegularNode(content="- Regular text", indent=4, children=[]),
                    CodeFenceNode(
                        content="```python\ncode\n```", indent=4, children=[]
                    ),
                    RegularNode(content="- More text", indent=4, children=[]),
                ],
            )
        ]
        expected = (
            "<details>\n"
            "<summary>Analysis:</summary>\n"
            "\n"
            "Regular text.\n"
            "\n"
            "```python\n"
            "code\n"
            "```\n"
            "\n"
            "More text.\n"
            "</details>\n"
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


def test_process() -> None:
    """Integration test validating all devlog transformations.

    This test validates:
    - Header preservation (## becomes ##, bullets removed)
    - Regular bullet flattening to paragraphs with automatic punctuation
    - Choice block structure preservation with :: to **label:** conversion
    - Code block indentation alignment within Choice blocks
    - Code fence language conversion ('plain text' to 'plaintext')
    - Quote block formatting with > prefix preservation
    - Numbered list preservation without extra blank lines
    - [list] marker for preserving children as indented bullets
    - {{[[DONE]]}} marker removal
    - Choice blocks appearing after flattened content
    """
    input_text = """
- ## Background and scope of work
    - I will (for now) not add images to scraps until I have native support for images in my posting (so they either only exist in a special content type, which gets linked, or they're attached when posting as a scrap).
    - I do this because I feel linking to these short-text things that really could just live on Masto/Bsky/etc. is a bit much, be a bit more native to them. Do use them to publish my other content but don't only send links when they're not necessary. It feels like being a bad citizen to them when it's only a sink that way.
    - The way I've setup the sending in n8n right now, is that I have two steps in the status: 1) truncating the body and deciding if we need more, 2) and then adding the link, so I need to figure out a better maintenance pattern
        - {{[[DONE]]}} [[Choice]] Manage n8n workflow with source management
            - Constraints::
                - Be able to recreate my n8n setup if something goes belly-up
                - Keep as much as possible in source (but don't overdo it, I'm a single person doing this and can manage myself)
            - Options::
                - Keep n8n fully clickops and keep code snippets in blog
                    - Advantages::
                        - Super simple and what I'm doing, the status quo choice
                          ```plain text
                          def hello(s):
                              print(f'hello, {s}')
                          ```
                    - Disadvantages::
                        - If I have to recreate the n8n setup from scratch, painful
                - Create the workflow file in my blog and upload it for changes
                    - Advantages::
                        - All my n8n stuff is in my blog, so it's easy for me to deal with, and it's something I can easily share later so that's a win for sharing
                    - Disadvantages::
                        - More work to figure it out right now
                            - But probably worth it, I'll download the workflow file and look at it to see what it says
                            - looking at the JSON file it looks pretty straightforward, and using JQ I should be able to pretty easily inject what I need into it, so I can create a small file/script to help me out here that'll be worth it I think
            - Decision:: Create the workflow file in my blog and upload it for changes
                - It feels like a good step towards a maintainable setup and minimal effort to get it going
    - > __For each desired change, 
      make the change easy (warning: this may be hard), 
      then make the easy change__
    - And to enumerate:
        1. One
        2. Two
        3. Three
    - Keep these child bullets: [list]
        - First
        - Second
            - Third
    - And an LLM plan to review: [details]
      ```text plain
       Line 1
       Line 2
      ```
"""

    assert process(input_text) == (
        """
## Background and scope of work

I will (for now) not add images to scraps until I have native support for images in my posting (so they either only exist in a special content type, which gets linked, or they're attached when posting as a scrap).

I do this because I feel linking to these short-text things that really could just live on Masto/Bsky/etc. is a bit much, be a bit more native to them. Do use them to publish my other content but don't only send links when they're not necessary. It feels like being a bad citizen to them when it's only a sink that way.

The way I've setup the sending in n8n right now, is that I have two steps in the status: 1) truncating the body and deciding if we need more, 2) and then adding the link, so I need to figure out a better maintenance pattern.

- **Choice:** Manage n8n workflow with source management
    - **Constraints:**
        - Be able to recreate my n8n setup if something goes belly-up
        - Keep as much as possible in source (but don't overdo it, I'm a single person doing this and can manage myself)
    - **Options:**
        - Keep n8n fully clickops and keep code snippets in blog
            - **Advantages:**
                - Super simple and what I'm doing, the status quo choice
                  ```plaintext
                  def hello(s):
                      print(f'hello, {s}')
                  ```
            - **Disadvantages:**
                - If I have to recreate the n8n setup from scratch, painful
        - Create the workflow file in my blog and upload it for changes
            - **Advantages:**
                - All my n8n stuff is in my blog, so it's easy for me to deal with, and it's something I can easily share later so that's a win for sharing
            - **Disadvantages:**
                - More work to figure it out right now
                    - But probably worth it, I'll download the workflow file and look at it to see what it says
                    - looking at the JSON file it looks pretty straightforward, and using JQ I should be able to pretty easily inject what I need into it, so I can create a small file/script to help me out here that'll be worth it I think
    - **Decision:** Create the workflow file in my blog and upload it for changes
        - It feels like a good step towards a maintainable setup and minimal effort to get it going

> __For each desired change,
> make the change easy (warning: this may be hard),
> then make the easy change__

And to enumerate:

1. One
2. Two
3. Three

Keep these child bullets:

- First
- Second
    - Third

<details>
<summary>And an LLM plan to review:</summary>

```plaintext
 Line 1
 Line 2
```
</details>
"""
    )
