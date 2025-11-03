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


def format_tree(nodes: list[dict]) -> str:
    """Format tree into final markdown output.

    Rules:
    - Choice blocks: Keep nested structure, convert [[Choice]] to **Choice:**
    - Numbered lists: Preserve as-is
    - Regular bullets: Flatten to paragraphs with punctuation
    """
    result = []
    for node in nodes:
        formatted = _format_node(node)
        if formatted:
            result.append(formatted)
    return "\n\n".join(result) + "\n" if result else ""


def _format_choice_child(node: dict, indent_level: int = 4) -> str:
    """Format a child of a choice block recursively.

    Args:
        node: The node to format
        indent_level: Current indentation level in spaces (4, 8, 12, etc.)

    Rules:
    - If content starts with "- ": format with "- " at current indentation
    - If content doesn't start with "- ": format without bullet at current indentation
    - Preserve content as-is (no automatic punctuation)
    - Recursively format children with indent_level + 4
    """
    content = node.get("content", "").strip()
    children = node.get("children", [])

    # Check if content starts with "- "
    has_bullet = content.startswith("- ")
    if has_bullet:
        content = content[2:]  # Remove "- " prefix

    # Format current node
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

    # For regular bullets, flatten all descendants
    # Collect all content from this node and its children recursively
    all_content = [content]
    _collect_all_content(node, all_content)

    # Add punctuation to each item if needed
    formatted_items = []
    for item in all_content:
        formatted_items.append(_add_punctuation(item))

    # Collect any choice_block children that need separate formatting
    choice_blocks = []
    _collect_choice_blocks(node, choice_blocks)

    # Join flattened content with blank lines between paragraphs
    result_parts = ["\n\n".join(formatted_items)]

    # Add formatted choice blocks
    for choice_block in choice_blocks:
        formatted_choice = _format_node(choice_block)
        if formatted_choice:
            result_parts.append(formatted_choice)

    return "\n\n".join(result_parts)


def _collect_choice_blocks(node: dict, result: list[dict]) -> None:
    """Recursively collect all choice_block children from a node's descendants."""
    children = node.get("children", [])
    for child in children:
        if child.get("type") == "choice_block":
            result.append(child)
            # Don't recurse into choice block children - they're part of the block
        else:
            # Recursively search in non-choice-block children
            _collect_choice_blocks(child, result)


def _collect_all_content(node: dict, result: list[str]) -> None:
    """Recursively collect all content from a node and its descendants.

    Skips choice_block nodes and their descendants since they should be
    formatted separately with their structure preserved.
    """
    children = node.get("children", [])
    for child in children:
        # Skip choice blocks - they should be formatted separately
        if child.get("type") == "choice_block":
            continue

        child_content = child.get("content", "").strip()
        # Remove bullet marker
        if child_content.startswith("- "):
            child_content = textwrap.dedent(child_content.replace("- ", "  ", 1))
        if child_content:
            result.append(child_content)
        # Recursively collect from grandchildren
        _collect_all_content(child, result)


def _add_punctuation(text: str) -> str:
    """Add period to text if it doesn't end with punctuation.

    Rules:
    - Don't add period if ends with: . ! ? : ) or smileys like :) :D etc.
    - Don't add period to headers (starting with #)
    - Don't add period to code fences (ending with ```)
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

    return format_tree(transformed)


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
