"""Roam Research to Markdown converter."""

import argparse
import re
import sys
import textwrap
from typing import NotRequired, TypedDict


class Node(TypedDict):
    """Represents a node in the parsed tree structure.

    Fields:
        content: The text content of the node (bullet marker may be included)
        indent: Indentation level in spaces (0, 4, 8, etc.)
        children: List of child nodes
        type: Optional node type marker (e.g., "choice_block")
        preserve_list: Optional flag to preserve list structure instead of flattening
        details_block: Optional flag to format as HTML details block
    """

    content: str
    indent: int
    children: list["Node"]
    type: NotRequired[str]
    preserve_list: NotRequired[bool]
    details_block: NotRequired[bool]


def _collect_bullet_groups(lines: list[str]) -> list[tuple[int, str]]:
    """Collect lines into bullet groups, handling continuation lines.

    Pass 1 of parsing: Groups lines belonging to each bullet together,
    handling continuation lines (lines without bullet markers that follow
    a bullet line).

    Args:
        lines: List of input lines to process

    Returns:
        List of (indent_level, content) tuples where:
        - indent_level: Indentation in spaces (0, 4, 8, etc.)
        - content: The bullet marker + all lines for this bullet (including
          continuation lines), normalized for indentation

    Processing:
        - Skips empty lines
        - Groups lines without bullet markers as continuations of previous bullet
        - Normalizes indentation after collecting all lines for a bullet
    """
    bullet_groups = []
    current_indent = None
    current_content_lines = []

    for line in lines:
        if not line.strip():
            # Skip empty lines entirely
            continue

        # Calculate indentation
        indent = len(line) - len(line.lstrip())
        stripped_content = line.strip()
        has_bullet = _has_bullet_marker(stripped_content)

        if has_bullet:
            # This is a new bullet line
            # First, finalize the previous group if it exists
            if current_content_lines:
                # Join collected lines and normalize
                combined_content = "\n".join(current_content_lines)
                normalized = _normalize_bullet_content(combined_content, current_indent)
                bullet_groups.append((current_indent, normalized))

            # Start a new group with this bullet line
            current_indent = indent
            current_content_lines = [stripped_content]
        else:
            # This is a continuation line (no bullet marker)
            if current_content_lines:
                # Append to current group, preserving original formatting
                current_content_lines.append(line)

    # Finalize the last group
    if current_content_lines:
        combined_content = "\n".join(current_content_lines)
        normalized = _normalize_bullet_content(combined_content, current_indent)
        bullet_groups.append((current_indent, normalized))

    return bullet_groups


def parse_roam_bullets(text: str) -> list[Node]:
    """Parse Roam-style indented bullets into tree structure.

    Two-pass approach for clarity:
    1. Pass 1 (_collect_bullet_groups): Collect lines into bullet groups,
       handling continuation lines and normalizing indentation
    2. Pass 2 (this function): Build tree structure from bullet groups

    Returns list of nodes where each node is:
    {
        'content': str,      # The line content including bullet marker
        'indent': int,       # Indentation level (0, 4, 8, etc.)
        'children': list     # List of child nodes
    }
    """
    if not text.strip():
        return []

    lines = text.split("\n")

    # Pass 1: Collect bullet groups with continuation lines handled
    bullet_groups = _collect_bullet_groups(lines)

    # Pass 2: Build tree structure from bullet groups
    root_nodes = []
    for indent, content in bullet_groups:
        node = {
            "content": content,
            "indent": indent,
            "children": [],
        }

        # Find parent and add as child, or add to root
        if indent == 0:
            root_nodes.append(node)
        else:
            parent = _find_parent(root_nodes, indent)
            if parent is not None:
                parent["children"].append(node)
            else:
                # No parent found, add to root (handles indented bullets without parents)
                root_nodes.append(node)

    return root_nodes


def _has_bullet_marker(content: str) -> bool:
    """Check if content starts with a bullet marker.

    Detects:
    - Unordered lists: starts with "- "
    - Numbered lists: starts with number followed by ". "
    """
    if content.startswith("- "):
        return True
    # Check for numbered list (e.g., "1. ", "2. ", etc.)
    if re.match(r"^\d+\.\s", content):
        return True
    return False


def _normalize_bullet_content(content: str, bullet_indent: int) -> str:
    """Normalize indentation in bullet content.

    Dedents continuation lines by the bullet's indentation level while
    maintaining minimum indentation equal to the bullet marker length.

    Args:
        content: The bullet content to normalize
        bullet_indent: The indentation level of the bullet (in spaces)

    Returns:
        Normalized content with consistent indentation
    """
    if not content:
        return content

    # Extract the bullet marker
    bullet_marker = None
    if content.startswith("- "):
        bullet_marker = "- "
    else:
        # Check for numbered list marker
        match = re.match(r"^(\d+\.\s)", content)
        if match:
            bullet_marker = match.group(1)

    if not bullet_marker:
        return content

    bullet_marker_len = len(bullet_marker)

    # Split into lines
    lines = content.split("\n")
    if len(lines) <= 1:
        return content  # No continuation lines, nothing to normalize

    # First line is the bullet line
    first_line = lines[0]
    continuation_lines = lines[1:]

    # Normalize each continuation line
    normalized_lines = [first_line]
    for line in continuation_lines:
        if line.strip():
            # Calculate current indentation
            current_indent = len(line) - len(line.lstrip())
            # Dedent by bullet indent, but maintain minimum of bullet marker length
            new_indent = max(current_indent - bullet_indent, bullet_marker_len)
            # Reconstruct line with new indentation
            normalized_lines.append(" " * new_indent + line.lstrip())
        else:
            # Preserve empty lines
            normalized_lines.append(line)

    return "\n".join(normalized_lines)


def _find_parent(nodes: list[Node], indent: int) -> Node | None:
    """Find the closest parent node with smaller indentation."""
    # Start from the end and traverse depth-first
    if not nodes:
        return None

    # Check the last node and its descendants
    def search_last_node(current_nodes):
        if not current_nodes:
            return None

        last_node = current_nodes[-1]

        # If last node has children, search there first
        if last_node["children"]:
            result = search_last_node(last_node["children"])
            if result is not None:
                return result

        # If last node has smaller indent, it's our parent
        if last_node["indent"] < indent:
            return last_node

        return None

    return search_last_node(nodes)


def transform_tree(nodes: list[Node]) -> list[Node]:
    """Transform tree by removing markers, filtering nodes, etc.

    Transformations:
    - Remove {{[[DONE]]}} and {{[[TODO]]}} markers
    - Remove #meta nodes and their children
    - Mark [[Choice]] blocks with special type
    - Convert code fence 'plain text' to 'plaintext'
    - Convert :: labels to **label:** format
    - Detect [list] marker and set preserve_list flag
    """
    # Filter out #meta nodes and transform the rest
    result = []
    for node in nodes:
        if _is_meta_node(node):
            continue

        # Create a copy of the node to avoid modifying the original
        transformed_node = {
            "content": node["content"],
            "indent": node["indent"],
            "children": transform_tree(node["children"]),
        }

        # Copy other keys (like 'type' if it exists)
        for key in node:
            if key not in ["content", "indent", "children"]:
                transformed_node[key] = node[key]

        # Apply transformations to content
        transformed_content = transformed_node["content"]

        # Check for [[Choice]] blocks before removing markers
        has_choice = "[[Choice]]" in transformed_content

        # Remove TODO/DONE markers
        transformed_content = re.sub(
            r"\{\{\[\[(DONE|TODO)\]\]\}\}\s*", "", transformed_content
        )

        # Convert :: labels to **label:** format
        transformed_content = _convert_double_colon_labels(transformed_content)

        # Detect and remove [list] marker
        has_list_marker, transformed_content = _detect_and_remove_list_marker(
            transformed_content
        )
        if has_list_marker:
            transformed_node["preserve_list"] = True

        # Detect and remove [details] marker
        has_details_marker, transformed_content = _detect_and_remove_details_marker(
            transformed_content
        )
        if has_details_marker:
            transformed_node["details_block"] = True

        transformed_node["content"] = transformed_content

        # Mark choice blocks
        if has_choice:
            transformed_node["type"] = "choice_block"

        result.append(transformed_node)

    return result


def _is_meta_node(node: Node) -> bool:
    """Check if a node is a #meta node."""
    content = node.get("content", "")
    # Check if the content contains #meta as a word
    return "#meta" in content and (
        content.startswith("- #meta ")
        or " #meta " in content
        or content.endswith("#meta")
    )


def _detect_and_remove_list_marker(content: str) -> tuple[bool, str]:
    """Detect and remove [list] marker from content.

    Returns:
        Tuple of (has_list_marker, cleaned_content)
        - has_list_marker: True if [list] marker was found and removed
        - cleaned_content: Content with [list] marker and trailing spaces removed
    """
    # Check if content ends with [list] (possibly with trailing spaces)
    if re.search(r"\[list\]\s*$", content):
        # Remove [list] and trailing spaces
        cleaned = re.sub(r"\s*\[list\]\s*$", "", content)
        return True, cleaned
    return False, content


def _detect_and_remove_details_marker(content: str) -> tuple[bool, str]:
    """Detect and remove [details] marker from content.

    Returns:
        Tuple of (has_details_marker, cleaned_content)
        - has_details_marker: True if [details] marker was found and removed
        - cleaned_content: Content with [details] marker and trailing spaces removed
    """
    # Check if content ends with [details] (possibly with trailing spaces)
    # Matches: [details] followed by optional spaces, then either newline or end of string
    if re.search(r"\[details\]\s*(?:\n|$)", content):
        # Remove [details] and all trailing spaces (including before newline if present)
        cleaned = re.sub(r"\s*\[details\]\s*$", "", content, flags=re.MULTILINE)
        return True, cleaned
    return False, content


def _convert_double_colon_labels(content: str) -> str:
    """Convert :: labels to **label:** format.

    Examples:
        "- Constraints::" -> "- **Constraints:**"
        "- Decision:: Go with this" -> "- **Decision:** Go with this"
    """
    # Pattern: text with :: followed by optional content
    # Matches: word_or_words:: optionally followed by anything
    pattern = r"(\s)([^:\s][^:]*?)::(\s|$)"
    replacement = r"\1**\2:**\3"
    return re.sub(pattern, replacement, content)


def _collect_and_format_numbered_items(
    nodes: list[Node], start_index: int
) -> tuple[str, int]:
    """Collect and format consecutive numbered list items.

    Collects consecutive numbered list items starting from start_index,
    formats them using _format_numbered_list_item, and returns the
    formatted result along with the next index to process.

    Args:
        nodes: List of nodes to process
        start_index: Index to start collecting from

    Returns:
        Tuple of (formatted_string, next_index) where:
        - formatted_string: Joined and rstripped numbered items (empty string if none)
        - next_index: Index of first non-numbered-list item after the sequence
    """
    numbered_items = []
    i = start_index

    # Collect consecutive numbered list items
    while i < len(nodes) and _is_numbered_list_item(nodes[i]):
        formatted = _format_numbered_list_item(nodes[i])
        if formatted:
            numbered_items.append(formatted)
        i += 1

    # Join numbered items: pure concatenation preserves all newlines
    # (items with children end with \n\n, items without end with \n)
    joined = "".join(numbered_items).rstrip("\n")

    return joined, i


def format_tree(nodes: list[Node]) -> str:
    """Format tree into final markdown output.

    Rules:
    - Choice blocks: Keep nested structure, convert [[Choice]] to **Choice:**
    - Numbered lists: Preserve as-is without blank lines between consecutive items
    - Regular bullets: Flatten to paragraphs with punctuation
    """
    if not nodes:
        return ""

    result = []
    i = 0
    while i < len(nodes):
        node = nodes[i]

        # Check if this is a numbered list item
        if _is_numbered_list_item(node):
            # Collect consecutive numbered list items
            joined, i = _collect_and_format_numbered_items(nodes, i)
            if joined:
                result.append(joined)
        else:
            # Regular node processing
            formatted = _format_node(node)
            if formatted:
                result.append(formatted)
            i += 1

    return "\n\n".join(result) + "\n" if result else ""


def _is_numbered_list_item(node: Node) -> bool:
    """Check if a node is a numbered list item (starts with digit followed by period)."""
    content = node.get("content", "").strip()
    return bool(re.match(r"^\d+\.\s", content))


def _format_numbered_list_item(node: Node) -> str:
    """Format a numbered list item with its children.

    Numbered list items should:
    - NOT have periods added (preserve as-is)
    - Children should be formatted and flattened
    - Return the item with newline(s) at the end for joining
    """
    content = node.get("content", "").strip()
    children = node.get("children", [])

    # Numbered items are preserved as-is, no punctuation added
    # Format and flatten children
    child_content = []
    for child in children:
        formatted_child = _format_node(child)
        if formatted_child:
            child_content.append(formatted_child)

    # Add children separated by blank lines
    if child_content:
        # When we have children, end with \n\n to separate from the next numbered item
        return content + "\n\n" + "\n\n".join(child_content) + "\n\n"
    else:
        # When no children, just end with single newline
        return content + "\n"


def _format_quote_block(content: str) -> str:
    """Format a quote block by preserving > prefixes on each line.

    Args:
        content: The content starting with "- > " or multi-line quote

    Returns:
        The formatted quote block with > prefix on each line, without trailing newline
    """
    # Remove the leading "- " bullet marker
    if content.startswith("- "):
        content = content[2:]

    # Split into lines
    lines = content.split("\n")
    formatted_lines = []

    for line in lines:
        # Remove leading/trailing whitespace to normalize
        stripped = line.strip()
        if stripped:
            # If line already starts with "> ", keep it; otherwise add it
            if not stripped.startswith("> "):
                formatted_lines.append("> " + stripped)
            else:
                formatted_lines.append(stripped)
        else:
            # Preserve empty lines if needed (though unlikely in quotes)
            formatted_lines.append(line)

    return "\n".join(formatted_lines)


def _format_preserve_list_children(children: list[Node], indent_level: int = 0) -> str:
    """Format children of a preserve_list node as indented bullets.

    Args:
        children: The child nodes to format
        indent_level: Current indentation level in spaces (0, 4, 8, etc.)

    Returns:
        Formatted children as indented bullets, without trailing newline
    """
    formatted_lines = []

    for child in children:
        content = child.get("content", "").strip()
        child_children = child.get("children", [])
        preserve_list_child = child.get("preserve_list", False)

        # Remove bullet marker
        if content.startswith("- "):
            content = content[2:]

        # Create indentation
        indent_str = " " * indent_level

        # Add current node as bullet
        formatted_lines.append(indent_str + "- " + content)

        # Handle children
        if preserve_list_child and child_children:
            # Recursively format preserve_list children with more indentation
            child_formatted = _format_preserve_list_children(
                child_children, indent_level + 4
            )
            if child_formatted:
                formatted_lines.append(child_formatted)
        elif child_children:
            # Non-preserve_list children should be flattened
            for grandchild in child_children:
                grandchild_content = grandchild.get("content", "").strip()
                if grandchild_content.startswith("- "):
                    grandchild_content = grandchild_content[2:]
                indent_str_child = " " * (indent_level + 4)
                formatted_lines.append(indent_str_child + "- " + grandchild_content)

    return "\n".join(formatted_lines)


def _format_multiline_choice_content(
    lines: list[str], has_bullet: bool, indent_level: int
) -> str:
    """Format multi-line content for choice blocks with proper indentation.

    Handles indentation of content that spans multiple lines (e.g., code blocks),
    preserving relative indentation within the content while aligning with the
    block's structure.

    Args:
        lines: The content lines to format (first line is the main content)
        has_bullet: Whether the first line should have a bullet marker ("- ")
        indent_level: Current indentation level in spaces (4, 8, 12, etc.)

    Returns:
        Formatted multi-line content as a single string with embedded newlines

    Indentation Rules:
        - First line gets indent_level (plus "- " if has_bullet)
        - If has_bullet: continuation lines get indent_level + 2
        - If no bullet: continuation lines get indent_level
        - Relative indentation within the content is preserved (e.g., code blocks)
        - Empty lines are preserved as-is
    """
    indent_str = " " * indent_level
    formatted_lines = []

    # Format first line with optional bullet marker
    if has_bullet:
        formatted_lines.append(indent_str + "- " + lines[0])
        # When there's a bullet, continuation lines align 2 spaces after the "- "
        continuation_indent = indent_level + 2
    else:
        formatted_lines.append(indent_str + lines[0])
        # When there's no bullet, continuation lines use the same indentation
        continuation_indent = indent_level

    # Find minimum indentation in continuation lines to preserve relative indentation.
    # This is critical for code blocks where relative indentation conveys structure.
    continuation_lines = lines[1:]
    leftmost_indent_in_content = None
    for line in continuation_lines:
        if line.strip():  # Only consider non-empty lines
            current_indent = len(line) - len(line.lstrip())
            if (
                leftmost_indent_in_content is None
                or current_indent < leftmost_indent_in_content
            ):
                leftmost_indent_in_content = current_indent

    # Format continuation lines, preserving their relative indentation
    for line in continuation_lines:
        stripped = line.lstrip()
        if stripped:
            # Calculate original indentation and preserve relative offset
            original_indent = len(line) - len(stripped)
            # relative_indent is the offset from the leftmost line
            # (e.g., if leftmost has 4 spaces and this line has 8, relative_indent is 4)
            relative_indent = original_indent - (leftmost_indent_in_content or 0)
            formatted_lines.append(
                " " * (continuation_indent + relative_indent) + stripped
            )
        else:
            # Preserve empty lines exactly as they are
            formatted_lines.append(line)

    return "\n".join(formatted_lines)


def _format_choice_child(node: Node, indent_level: int = 4) -> str:
    """Format a child of a choice block recursively.

    Args:
        node: The node to format
        indent_level: Current indentation level in spaces (4, 8, 12, etc.)

    Rules:
    - If content starts with "- ": format with "- " at current indentation
    - If content doesn't start with "- ": format without bullet at current indentation
    - Preserve content as-is (no automatic punctuation)
    - For multi-line content with code blocks: indent continuation lines at indent_level + 2
    - Recursively format children with indent_level + 4
    """
    content = node.get("content", "").strip()
    children = node.get("children", [])

    # Check if content starts with "- "
    has_bullet = content.startswith("- ")
    if has_bullet:
        content = content[2:]  # Remove "- " prefix

    # Handle multi-line content (e.g., content with code blocks)
    if "\n" in content:
        lines = content.split("\n")
        # Extract and format the multi-line content with proper indentation
        formatted_content = _format_multiline_choice_content(
            lines, has_bullet, indent_level
        )
        formatted_parts = [formatted_content]
    else:
        # Single-line content
        indent_str = " " * indent_level
        if has_bullet:
            formatted_parts = [indent_str + "- " + content]
        else:
            formatted_parts = [indent_str + content]

    # Recursively format children
    for child in children:
        formatted_child = _format_choice_child(child, indent_level + 4)
        if formatted_child:
            formatted_parts.append(formatted_child)

    return "\n".join(formatted_parts)


def _format_quote_node(node: Node) -> str:
    """Format a quote block node.

    Args:
        node: A node with content starting with "- > "

    Returns:
        Formatted quote block with > prefix on each line
    """
    content = node.get("content", "").strip()
    # Format the quote block (removes bullet marker internally)
    return _format_quote_block(content)


def _format_choice_node(node: Node) -> str:
    """Format a choice block node.

    Args:
        node: A node with type == "choice_block"

    Returns:
        Formatted choice block with nested structure preserved
    """
    content = node.get("content", "").strip()
    children = node.get("children", [])

    # Remove bullet marker if present, by making it a space so we can dedent
    if content.startswith("- "):
        content = content.replace("- ", "  ", 1)
        content = textwrap.dedent(content)

    # Convert [[Choice]] to **Choice:**
    content = re.sub(r"\[\[Choice\]\]", "**Choice:**", content)

    # Format the title with "- " prefix
    formatted_parts = ["- " + content]

    # Format children with proper indentation
    for child in children:
        formatted_child = _format_choice_child(child, indent_level=4)
        if formatted_child:
            formatted_parts.append(formatted_child)

    return "\n".join(formatted_parts)


def _format_preserve_list_node(node: Node) -> str:
    """Format a node with preserve_list flag.

    Args:
        node: A node with preserve_list == True

    Returns:
        Formatted node with children preserved as indented bullets
    """
    content = node.get("content", "").strip()
    children = node.get("children", [])

    # Remove bullet marker if present
    if content.startswith("- "):
        content = content.replace("- ", "  ", 1)
        content = textwrap.dedent(content)

    # Format parent content: ensure it ends with a colon (no period)
    if not content.endswith(":"):
        parent_formatted = content + ":"
    else:
        parent_formatted = content

    # Format children as indented bullets
    formatted_children = _format_preserve_list_children(children, indent_level=0)

    if formatted_children:
        return parent_formatted + "\n\n" + formatted_children
    else:
        return parent_formatted


def _format_details_node(node: Node) -> str:
    """Format a node with details_block flag as HTML details/summary.

    Args:
        node: A node with details_block == True

    Returns:
        Formatted HTML details block with summary and flattened children
    """
    content = node.get("content", "").strip()
    children = node.get("children", [])

    # Remove bullet marker if present
    if content.startswith("- "):
        content = content.replace("- ", "  ", 1)
        content = textwrap.dedent(content)

    # Split content into first line (summary) and continuation lines
    lines = content.split("\n", 1)
    summary_content = lines[0].strip()
    continuation_content = lines[1] if len(lines) > 1 else ""

    # Format children - flatten them like regular bullets
    child_parts = []

    # First, add any continuation lines from the content itself
    if continuation_content.strip():
        # Process continuation lines as if they were child content
        # Strip leading indentation and format them
        continuation_lines = continuation_content.split("\n")
        continuation_text = "\n".join(continuation_lines).strip()
        # Don't add punctuation for code blocks or already formatted content
        if not continuation_text.startswith("```"):
            continuation_text = _add_punctuation(continuation_text)
        child_parts.append(continuation_text)

    # Then add actual child nodes
    for child in children:
        formatted_child = _format_node(child)
        if formatted_child:
            child_parts.append(formatted_child)

    # Build the details block
    if child_parts:
        # Join children with blank lines (double newline separation)
        children_formatted = "\n\n".join(child_parts)
        # Structure: <details>\n<summary>content</summary>\n\nchildren\n</details>
        return f"<details>\n<summary>{summary_content}</summary>\n\n{children_formatted}\n</details>"
    else:
        # No children case
        return f"<details>\n<summary>{summary_content}</summary>\n</details>"


def _format_regular_node(node: Node) -> str:
    """Format a regular bullet node with flattening.

    Args:
        node: A node without special type or preserve_list flag

    Returns:
        Formatted node with children flattened and punctuation added
    """
    content = node.get("content", "").strip()
    children = node.get("children", [])

    # Remove bullet marker if present, by making it a space so we can dedent
    if content.startswith("- "):
        content = content.replace("- ", "  ", 1)
        content = textwrap.dedent(content)

    # For regular bullets, process children in order maintaining sequence
    # This includes regular content that gets flattened and choice blocks inline
    result_parts = []

    # Add punctuation to root content if present
    if content:
        result_parts.append(_add_punctuation(content))

    # Process children, detecting consecutive numbered list items
    i = 0
    while i < len(children):
        child = children[i]

        # Check if this starts a sequence of numbered list items
        if _is_numbered_list_item(child):
            # Collect consecutive numbered list items
            joined, i = _collect_and_format_numbered_items(children, i)
            if joined:
                result_parts.append(joined)
        else:
            # Check if child is a choice block
            if child.get("type") == "choice_block":
                # Format choice block and add it
                formatted_child = _format_node(child)
                if formatted_child:
                    result_parts.append(formatted_child)
            else:
                # Format non-choice children and flatten their content
                formatted_child = _format_node(child)
                if formatted_child:
                    result_parts.append(formatted_child)
            i += 1

    return "\n\n".join(result_parts)


def _format_node(node: Node, is_choice_child: bool = False) -> str:
    """Format a single node by dispatching to type-specific handlers.

    Args:
        node: The node to format
        is_choice_child: True if this node is a child of a choice block (unused, kept for compatibility)

    Dispatches to:
    - _format_quote_node: For quote blocks (content starts with "- > ")
    - _format_choice_node: For choice blocks (type == "choice_block")
    - _format_preserve_list_node: For nodes with preserve_list flag
    - _format_details_node: For details blocks (details_block == True)
    - _format_regular_node: For regular bullets with flattening
    """
    content = node.get("content", "").strip()

    # Dispatch to appropriate handler based on node type
    if content.startswith("- > "):
        return _format_quote_node(node)
    if node.get("type") == "choice_block":
        return _format_choice_node(node)
    if node.get("preserve_list"):
        return _format_preserve_list_node(node)
    if node.get("details_block"):
        return _format_details_node(node)
    return _format_regular_node(node)


def _add_punctuation(text: str) -> str:
    """Add period to text if it doesn't end with punctuation.

    Rules:
    - Don't add period if ends with: . ! ? : ) or smileys like :) :D etc.
    - Don't add period to headers (starting with #)
    - Don't add period to code fences (ending with ```)
    - Don't add period to numbered lists (starting with digit. )
    - DO add period if no punctuation at end
    """
    text = text.strip()
    if not text:
        return text

    # Don't add punctuation to headers
    if text.startswith("#"):
        return text

    # Don't add punctuation to code fences
    if text.endswith("```"):
        return text

    # Don't add punctuation to numbered lists
    if re.match(r"^\d+\.\s", text):
        return text

    # Check if ends with punctuation or smiley
    if re.search(r"[.!?:)]\s*$", text):
        # Already has punctuation
        return text

    # Check for smileys (like :) :D ;) etc.)
    if re.search(r":\)+$|:D+$|;-?\)+$", text):
        return text

    # Check if it's a bold label (like **Constraints:**)
    if text.endswith(":**"):
        return text

    # Add period
    return text + "."


def process(content: str) -> str:
    """Process Roam Research notes into Markdown format."""
    parsed = parse_roam_bullets(content)
    transformed = transform_tree(parsed)
    formatted = format_tree(transformed)

    # Convert 'plain text' or 'text plain' code fence to 'plaintext'
    formatted = re.sub(r"```(?:plain text|text plain)", "```plaintext", formatted)

    # Preserve leading newline from input
    if content.startswith("\n"):
        formatted = "\n" + formatted

    return formatted


def main() -> int:
    """Main CLI entry point.

    Usage:
        python -m blog.devlog input.md
        cat input.md | python -m blog.devlog
        python -m blog.devlog < input.md

    Returns:
        0 on success, non-zero on error
    """
    parser = argparse.ArgumentParser(
        description="Convert Roam Research notes to Markdown format"
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="Input file to convert (reads from stdin if not provided)",
    )

    args = parser.parse_args()

    try:
        # Read input
        if args.file:
            try:
                with open(args.file, "r") as f:
                    content = f.read()
            except FileNotFoundError:
                sys.stderr.write(f"Error: File '{args.file}' not found\n")
                return 1
        else:
            content = sys.stdin.read()

        # Process through pipeline
        formatted = process(content)

        # Output
        sys.stdout.write(formatted)
        return 0

    except Exception as e:
        sys.stderr.write(f"Error parsing input: {e}\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
