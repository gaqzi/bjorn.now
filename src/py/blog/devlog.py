"""Roam Research to Markdown converter."""

import argparse
import re
import sys


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

    for line in lines:
        if not line.strip():
            continue

        # Calculate indentation level (4 spaces = 1 level)
        indent = len(line) - len(line.lstrip())
        content = line.strip()

        node = {
            "content": content,
            "indent": indent,
            "children": [],
        }

        # Find parent and add as child
        if indent == 0:
            root_nodes.append(node)
        else:
            # Find the parent node
            parent = _find_parent(root_nodes, indent)
            if parent is not None:
                parent["children"].append(node)

    return root_nodes


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


def _format_node(node: dict, is_choice_child: bool = False) -> str:
    """Format a single node and its children.

    Args:
        node: The node to format
        is_choice_child: True if this node is a child of a choice block
    """
    content = node.get("content", "").strip()
    node_type = node.get("type")
    children = node.get("children", [])

    # Remove bullet marker if present
    if content.startswith("- "):
        content = content[2:]

    # Handle choice blocks
    if node_type == "choice_block":
        # Convert [[Choice]] to **Choice:**
        content = re.sub(r"\[\[Choice\]\]", "**Choice:**", content)

        # Format the title and children
        formatted_parts = [content]

        # Format children (they are direct children of choice block)
        for child in children:
            formatted_child = _format_node(child, is_choice_child=True)
            if formatted_child:
                formatted_parts.append(formatted_child)

        return "\n\n".join(formatted_parts)

    # For choice block children, preserve nested bullets
    if is_choice_child and children:
        formatted_parts = [content]

        # Format children as nested bullets
        for child in children:
            child_content = child.get("content", "").strip()
            # Remove bullet marker
            if child_content.startswith("- "):
                child_content = child_content[2:]
            formatted_parts.append("- " + child_content)

        return "\n".join(formatted_parts)

    # For regular bullets, flatten all descendants
    # Collect all content from this node and its children recursively
    all_content = [content]
    _collect_all_content(node, all_content)

    # Add punctuation to each item if needed
    formatted_items = []
    for item in all_content:
        formatted_items.append(_add_punctuation(item))

    # Join with blank lines between paragraphs
    return "\n\n".join(formatted_items)


def _collect_all_content(node: dict, result: list[str]) -> None:
    """Recursively collect all content from a node and its descendants."""
    children = node.get("children", [])
    for child in children:
        child_content = child.get("content", "").strip()
        # Remove bullet marker
        if child_content.startswith("- "):
            child_content = child_content[2:]
        if child_content:
            result.append(child_content)
        # Recursively collect from grandchildren
        _collect_all_content(child, result)


def _add_punctuation(text: str) -> str:
    """Add period to text if it doesn't end with punctuation.

    Rules:
    - Don't add period if ends with: . ! ? : ) or smileys like :) :D etc.
    - DO add period if no punctuation at end
    """
    text = text.strip()
    if not text:
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
        parsed = parse_roam_bullets(content)
        transformed = transform_tree(parsed)
        formatted = format_tree(transformed)

        # Output
        sys.stdout.write(formatted)
        return 0

    except Exception as e:
        sys.stderr.write(f"Error parsing input: {e}\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
