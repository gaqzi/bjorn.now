"""Roam Research to Markdown converter."""

import argparse
import re
import sys
import textwrap


def parse_roam_bullets(text: str) -> list[dict]:
    """Parse Roam-style indented bullets into tree structure.

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
    root_nodes = []
    last_node = None  # Track the most recent node for continuation lines

    for line in lines:
        if not line.strip():
            continue

        # Calculate indentation level (4 spaces = 1 level)
        indent = len(line) - len(line.lstrip())

        # Check if this line has a bullet marker
        stripped_content = line.strip()
        has_bullet = _has_bullet_marker(stripped_content)

        # If no bullet marker, this is a continuation line
        if not has_bullet and last_node is not None:
            # Append to the last node's content, preserving the original line format
            last_node["content"] += "\n" + line
            continue

        # Normalize the previous node now that it's complete
        if last_node is not None:
            last_node["content"] = _normalize_bullet_content(
                last_node["content"], last_node["indent"]
            )

        content = stripped_content

        node = {
            "content": content,
            "indent": indent,
            "children": [],
        }

        # Find parent and add as child
        if indent == 0:
            root_nodes.append(node)
            last_node = node
        else:
            # Find the parent node
            parent = _find_parent(root_nodes, indent)
            if parent is not None:
                parent["children"].append(node)
                last_node = node
            else:
                # No parent found, add to root (handles indented bullets without parents)
                root_nodes.append(node)
                last_node = node

    # Normalize the final node
    if last_node is not None:
        last_node["content"] = _normalize_bullet_content(
            last_node["content"], last_node["indent"]
        )

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


def _find_parent(nodes: list[dict], indent: int) -> dict | None:
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


def transform_tree(nodes: list[dict]) -> list[dict]:
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

        transformed_node["content"] = transformed_content

        # Mark choice blocks
        if has_choice:
            transformed_node["type"] = "choice_block"

        result.append(transformed_node)

    return result


def _is_meta_node(node: dict) -> bool:
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
    nodes: list[dict], start_index: int
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


def format_tree(nodes: list[dict]) -> str:
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


def _is_numbered_list_item(node: dict) -> bool:
    """Check if a node is a numbered list item (starts with digit followed by period)."""
    content = node.get("content", "").strip()
    return bool(re.match(r"^\d+\.\s", content))


def _format_numbered_list_item(node: dict) -> str:
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


def _format_preserve_list_children(children: list[dict], indent_level: int = 0) -> str:
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


def _format_choice_child(node: dict, indent_level: int = 4) -> str:
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
        indent_str = " " * indent_level
        # First line gets the bullet if present
        if has_bullet:
            formatted_lines = [indent_str + "- " + lines[0]]
            # When there's a bullet, continuation lines get indented at indent_level + 2
            continuation_indent_base = indent_level + 2
        else:
            formatted_lines = [indent_str + lines[0]]
            # When there's no bullet, continuation lines get the same indent as the first line
            continuation_indent_base = indent_level

        # Find minimum indentation in continuation lines to preserve relative indentation
        continuation_lines = lines[1:]
        min_indent = None
        for line in continuation_lines:
            if line.strip():  # Only consider non-empty lines
                current_indent = len(line) - len(line.lstrip())
                if min_indent is None or current_indent < min_indent:
                    min_indent = current_indent

        for line in continuation_lines:
            stripped = line.lstrip()
            if stripped:
                # Calculate how much indentation the original line had
                original_indent = len(line) - len(stripped)
                # Preserve relative indentation within code blocks
                # relative_indent is the difference from the minimum
                relative_indent = original_indent - (min_indent or 0)
                formatted_lines.append(
                    " " * (continuation_indent_base + relative_indent) + stripped
                )
            else:
                # Preserve empty lines
                formatted_lines.append(line)

        formatted_parts = ["\n".join(formatted_lines)]
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


def _format_node(node: dict, is_choice_child: bool = False) -> str:
    """Format a single node and its children.

    Args:
        node: The node to format
        is_choice_child: True if this node is a child of a choice block
    """
    content = node.get("content", "").strip()
    node_type = node.get("type")
    children = node.get("children", [])
    preserve_list = node.get("preserve_list", False)

    # Check for quote blocks (content starts with "> " after bullet marker)
    is_quote_block = False
    if content.startswith("- > "):
        is_quote_block = True
        # Remove bullet marker and format as quote block
        content = _format_quote_block(content)
        return content if content else ""

    # Remove bullet marker if present, by making it a space so we can dedent
    if content.startswith("- "):
        content = content.replace("- ", "  ", 1)
        content = textwrap.dedent(content)

    # Handle choice blocks
    if node_type == "choice_block":
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

    # Handle preserve_list nodes
    if preserve_list:
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

    # Convert 'plain text' code fence to 'plaintext'
    formatted = re.sub(r"```plain text", "```plaintext", formatted)

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
