"""Roam Research to Markdown converter."""

import argparse
import re
import sys
import textwrap
from abc import ABC, abstractmethod
from typing import NotRequired, TypedDict


class NodeDict(TypedDict):
    """Represents a node in the parsed tree structure (dict-based).

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
    children: list["NodeDict"]
    type: NotRequired[str]
    preserve_list: NotRequired[bool]
    details_block: NotRequired[bool]


class Node(ABC):
    """Abstract base class for tree nodes."""

    def __init__(self, content: str, indent: int, children: list):
        """Initialize a node.

        Args:
            content: The text content of the node (bullet marker may be included)
            indent: Indentation level in spaces (0, 4, 8, etc.)
            children: List of child nodes (can be Node objects or dicts)
        """
        self.content = content
        self.indent = indent
        self.children = children

    @abstractmethod
    def modify(self, fn):
        """Apply a function to this node's content and recurse to children.

        Args:
            fn: Function to apply to content

        Returns:
            Modified node
        """
        pass

    @abstractmethod
    def __str__(self) -> str:
        """Format this node as a string.

        Returns:
            Formatted string representation
        """
        pass

    @classmethod
    @abstractmethod
    def matches(cls, content: str, **flags) -> bool:
        """Check if this node type matches the given content and flags.

        Args:
            content: The node content
            **flags: Additional flags (e.g., type, preserve_list, details_block)

        Returns:
            True if this node type should handle this content
        """
        pass

    def __eq__(self, other) -> bool:
        """Compare two nodes for equality.

        Args:
            other: The other object to compare with

        Returns:
            True if both nodes are the same type and have equal attributes
        """
        if type(self) != type(other):
            return False
        # Use content property for comparison (works for all nodes including CodeFenceNode)
        return (
            self.content == other.content
            and self.indent == other.indent
            and self.children == other.children
        )

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging.

        Returns:
            String representation including class name and attributes
        """
        return f"{self.__class__.__name__}(content={self.content!r}, indent={self.indent!r}, children={self.children!r})"


class ChoiceNode(Node):
    """Node representing a choice block with [[Choice]] marker."""

    @classmethod
    def matches(cls, content: str, **flags) -> bool:
        """Match nodes with type == "choice_block"."""
        return flags.get("type") == "choice_block"

    def modify(self, fn):
        """Apply function to content and recurse to children."""
        modified_content = fn(self.content)
        modified_children = [child.modify(fn) for child in self.children]
        return ChoiceNode(modified_content, self.indent, modified_children)

    def __str__(self) -> str:
        """Format choice block with nested structure preserved."""
        content = self.content.strip()

        # Remove bullet marker if present, by making it a space so we can dedent
        if content.startswith("- "):
            content = content.replace("- ", "  ", 1)
            content = _dedent_preserving_fences(content)

        # Convert [[Choice]] to **Choice:**
        content = re.sub(r"\[\[Choice\]\]", "**Choice:**", content)

        # Format the title with "- " prefix
        formatted_parts = ["- " + content]

        # Format children with proper indentation
        for child in self.children:
            formatted_child = self._format_choice_child(child, indent_level=4)
            if formatted_child:
                formatted_parts.append(formatted_child)

        return "\n".join(formatted_parts)

    def _format_choice_child(self, node, indent_level: int = 4) -> str:
        """Format a child of a choice block recursively.

        Args:
            node: The node to format (Node object)
            indent_level: Current indentation level in spaces (4, 8, 12, etc.)

        Rules:
        - If content starts with "- ": format with "- " at current indentation
        - If content doesn't start with "- ": format without bullet at current indentation
        - Preserve content as-is (no automatic punctuation)
        - For multi-line content with code blocks: indent continuation lines at indent_level + 2
        - Recursively format children with indent_level + 4
        """
        content = node.content.strip()
        children = node.children

        # Check if content starts with "- "
        has_bullet = content.startswith("- ")
        if has_bullet:
            content = content[2:]  # Remove "- " prefix

        # Handle multi-line content (e.g., content with code blocks)
        if "\n" in content:
            lines = content.split("\n")
            # Extract and format the multi-line content with proper indentation
            formatted_content = self._format_multiline_choice_content(
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
            formatted_child = self._format_choice_child(child, indent_level + 4)
            if formatted_child:
                formatted_parts.append(formatted_child)

        return "\n".join(formatted_parts)

    def _format_multiline_choice_content(
        self, lines: list[str], has_bullet: bool, indent_level: int
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


class DetailsNode(Node):
    """Node representing a details block with [details] marker."""

    @classmethod
    def matches(cls, content: str, **flags) -> bool:
        """Match nodes with details_block == True."""
        return flags.get("details_block") == True

    def modify(self, fn):
        """Apply function to content and recurse to children."""
        modified_content = fn(self.content)
        modified_children = [child.modify(fn) for child in self.children]
        return DetailsNode(modified_content, self.indent, modified_children)

    def __str__(self) -> str:
        """Format details block as HTML details/summary."""
        content = self.content.strip()

        # Remove bullet marker if present
        if content.startswith("- "):
            content = content.replace("- ", "  ", 1)
            content = _dedent_preserving_fences(content)

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
        for child in self.children:
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


class NumberedListNode(Node):
    """Node representing a numbered list item (starts with digit followed by period)."""

    @classmethod
    def matches(cls, content: str, **flags) -> bool:
        r"""Match nodes with content matching numbered list pattern ^\d+\."""
        return bool(re.match(r"^\d+\.\s", content.strip()))

    def modify(self, fn):
        """Apply function to content and recurse to children."""
        modified_content = fn(self.content)
        modified_children = [child.modify(fn) for child in self.children]
        return NumberedListNode(modified_content, self.indent, modified_children)

    def __str__(self) -> str:
        """Format numbered list item with its children.

        Numbered list items should:
        - Preserve numbering (no bullet removal)
        - NOT have periods added (preserve as-is)
        - Children should be formatted and flattened
        - No extra blank lines between consecutive items
        """
        content = self.content.strip()

        # Format and flatten children
        child_content = []
        for child in self.children:
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


class QuoteNode(Node):
    """Node representing a quote block (starts with "- > ")."""

    @classmethod
    def matches(cls, content: str, **flags) -> bool:
        """Match nodes with content starting with "- > "."""
        return content.strip().startswith("- > ")

    def modify(self, fn):
        """Apply function to content and recurse to children."""
        modified_content = fn(self.content)
        modified_children = [child.modify(fn) for child in self.children]
        return QuoteNode(modified_content, self.indent, modified_children)

    def __str__(self) -> str:
        """Format quote block by preserving > prefixes on each line.

        Removes the leading "- " bullet marker and ensures each line
        has the "> " prefix.
        """
        content = self.content.strip()

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


class CodeFenceNode(Node):
    """Node representing a code fence (contains triple backticks).

    Protects code fence content from transformations by parsing and storing
    fences separately from pre/post fence text.
    """

    def __init__(self, content: str, indent: int, children: list):
        """Initialize a code fence node and parse fence content.

        Args:
            content: The text content including code fences
            indent: Indentation level in spaces
            children: List of child nodes
        """
        # Store indent and children like regular nodes
        self.indent = indent
        self.children = children

        # Parse content to extract fences
        self._parse_content(content)

    def _parse_content(self, content: str):
        """Parse content to extract pre-fence text, fences, and post-fence text.

        Args:
            content: The full content string to parse
        """
        # Find all fence blocks - match opening ```, content, closing ```
        fence_pattern = r"```[^\n]*\n(?:.*?\n)?```"
        matches = list(re.finditer(fence_pattern, content, re.DOTALL))

        if not matches:
            # No fences found
            self._pre_fence_text = content
            self._fences = []
            self._post_fence_text = ""
            return

        # Extract pre-fence text (everything before first fence)
        first_fence_start = matches[0].start()
        self._pre_fence_text = content[:first_fence_start]

        # Extract each fence as (language, code_content)
        self._fences = []
        last_pos = first_fence_start

        for match in matches:
            # Add any text between previous fence and this one to post-fence
            # (This will be empty for the first fence since last_pos == first_fence_start)
            between_text = content[last_pos : match.start()]
            if between_text and self._fences:
                # If there's text between fences, append it to post_fence_text
                # and it will be part of the reconstruction
                pass

            fence_text = match.group(0)
            # Parse the fence to extract language and code
            lines = fence_text.split("\n")
            first_line = lines[0]
            language = first_line[3:].strip() if len(first_line) > 3 else ""

            # Extract code content (lines between opening and closing ```)
            if len(lines) > 2:
                # Normal case: opening, content lines, closing
                code_lines = lines[1:-1]
                code_content = "\n".join(code_lines)
            elif len(lines) == 2:
                # Edge case: opening line, closing line (no content)
                code_content = ""
            else:
                # Edge case: single line (malformed, but handle gracefully)
                code_content = ""

            self._fences.append((language, code_content))
            last_pos = match.end()

        # Extract post-fence text (everything after last fence)
        self._post_fence_text = content[last_pos:]

    @property
    def content(self) -> str:
        """Reconstruct content from pre-fence text, fences, and post-fence text.

        Returns:
            Reconstructed content string
        """
        parts = [self._pre_fence_text]

        for language, code_content in self._fences:
            fence_text = f"```{language}\n{code_content}\n```"
            parts.append(fence_text)

        parts.append(self._post_fence_text)

        return "".join(parts)

    @content.setter
    def content(self, value: str):
        """Parse and set content from value.

        Args:
            value: New content to parse and set
        """
        self._parse_content(value)

    @classmethod
    def matches(cls, content: str, **flags) -> bool:
        """Match nodes with content containing triple backticks (```)."""
        return "```" in content

    def modify(self, fn):
        """Apply function to pre/post fence text only, never to fence content.

        Args:
            fn: Function to apply to non-fence text

        Returns:
            New CodeFenceNode with modified pre/post text
        """
        # Apply fn only to pre and post fence text (not to fences themselves)
        modified_pre = (
            fn(self._pre_fence_text) if self._pre_fence_text else self._pre_fence_text
        )
        modified_post = (
            fn(self._post_fence_text)
            if self._post_fence_text
            else self._post_fence_text
        )

        # Reconstruct content with modified pre/post but unchanged fences
        parts = [modified_pre]
        for language, code_content in self._fences:
            fence_text = f"```{language}\n{code_content}\n```"
            parts.append(fence_text)
        parts.append(modified_post)

        modified_content = "".join(parts)

        # Recurse to children
        modified_children = [child.modify(fn) for child in self.children]

        return CodeFenceNode(modified_content, self.indent, modified_children)

    def __str__(self) -> str:
        """Format code fence content.

        Returns content with indentation alignment and bullet marker stripped.
        """
        content = self.content

        # Remove bullet marker if present from the entire content
        # We need to handle this carefully to maintain proper indentation
        if content.strip().startswith("- "):
            # Find where the bullet marker starts
            lines = content.split("\n")
            first_line = lines[0]

            # Remove bullet from first line
            if first_line.strip().startswith("- "):
                # Replace "- " with two spaces, then dedent everything
                first_line = first_line.replace("- ", "  ", 1)
                lines[0] = first_line
                content = "\n".join(lines)
                # Dedent the entire content while preserving fence indentation
                content = _dedent_preserving_fences(content)

        return content


class PreserveListNode(Node):
    """Node representing a list with preserve_list flag to preserve children as indented bullets."""

    @classmethod
    def matches(cls, content: str, **flags) -> bool:
        """Match nodes with preserve_list == True."""
        return flags.get("preserve_list") == True

    def modify(self, fn):
        """Apply function to content and recurse to children."""
        modified_content = fn(self.content)
        modified_children = [child.modify(fn) for child in self.children]
        return PreserveListNode(modified_content, self.indent, modified_children)

    def __str__(self) -> str:
        """Format preserve_list node with children preserved as indented bullets.

        No flattening occurs - children maintain their bullet structure.
        """
        content = self.content.strip()

        # Remove bullet marker if present
        if content.startswith("- "):
            content = content.replace("- ", "  ", 1)
            content = _dedent_preserving_fences(content)

        # Format parent content: ensure it ends with a colon (no period)
        if not content.endswith(":"):
            parent_formatted = content + ":"
        else:
            parent_formatted = content

        # Format children as indented bullets
        formatted_children = self._format_preserve_list_children(
            self.children, indent_level=0
        )

        if formatted_children:
            return parent_formatted + "\n\n" + formatted_children
        else:
            return parent_formatted

    def _format_preserve_list_children(
        self, children: list, indent_level: int = 0
    ) -> str:
        """Format children of a preserve_list node as indented bullets.

        Args:
            children: The child nodes to format (Node objects)
            indent_level: Current indentation level in spaces (0, 4, 8, etc.)

        Returns:
            Formatted children as indented bullets, without trailing newline
        """
        formatted_lines = []

        for child in children:
            content = child.content.strip()
            child_children = child.children
            preserve_list_child = isinstance(child, PreserveListNode)

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
                child_formatted = self._format_preserve_list_children(
                    child_children, indent_level + 4
                )
                if child_formatted:
                    formatted_lines.append(child_formatted)
            elif child_children:
                # Non-preserve_list children should be flattened
                for grandchild in child_children:
                    grandchild_content = grandchild.content.strip()
                    if grandchild_content.startswith("- "):
                        grandchild_content = grandchild_content[2:]
                    indent_str_child = " " * (indent_level + 4)
                    formatted_lines.append(indent_str_child + "- " + grandchild_content)

        return "\n".join(formatted_lines)


class RegularNode(Node):
    """Node representing a regular bullet (default fallback)."""

    @classmethod
    def matches(cls, content: str, **flags) -> bool:
        """Match all nodes (this is the fallback)."""
        return True

    def modify(self, fn):
        """Apply function to content and recurse to children."""
        modified_content = fn(self.content)
        modified_children = [child.modify(fn) for child in self.children]
        return RegularNode(modified_content, self.indent, modified_children)

    def __str__(self) -> str:
        """Format regular bullet node with flattening.

        Returns:
            Formatted node with children flattened and punctuation added
        """
        content = self.content.strip()

        # Remove bullet marker if present, by making it a space so we can dedent
        if content.startswith("- "):
            content = content.replace("- ", "  ", 1)
            content = _dedent_preserving_fences(content)

        # For regular bullets, process children in order maintaining sequence
        # This includes regular content that gets flattened and choice blocks inline
        result_parts = []

        # Add punctuation to root content if present
        if content:
            result_parts.append(_add_punctuation(content))

        # Process children, detecting consecutive numbered list items
        i = 0
        while i < len(self.children):
            child = self.children[i]

            # Check if this starts a sequence of numbered list items
            if _is_numbered_list_item(child):
                # Collect consecutive numbered list items
                joined, i = _collect_and_format_numbered_items(self.children, i)
                if joined:
                    result_parts.append(joined)
            else:
                # Check if child is a choice block
                is_choice = isinstance(child, ChoiceNode)
                if is_choice:
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


def _dedent_preserving_fences(content: str) -> str:
    """Dedent content while preserving relative indentation inside code fences.

    Args:
        content: The string to dedent

    Returns:
        Dedented string with code fence relative indentation preserved

    Processing:
        - Detects code fence boundaries (triple backticks)
        - Uses minimum of fence and content indentation as baseline
        - Dedents all content by the baseline indentation
        - Preserves relative indentation within fence content
        - Preserves blank line whitespace inside fences
    """
    if not content:
        return content

    # Check if there are any code fences
    if "```" not in content:
        # No fences, just dedent normally
        return textwrap.dedent(content)

    # Find the indentation of fence opening lines and content lines inside fences
    lines = content.split("\n")
    fence_indent = None
    min_content_indent = None
    in_fence = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            if not in_fence:
                # Opening fence - record its indentation
                indent = len(line) - len(line.lstrip())
                if fence_indent is None or indent < fence_indent:
                    fence_indent = indent
            in_fence = not in_fence
        elif in_fence and stripped:
            # Content line inside fence - record its indentation
            indent = len(line) - len(line.lstrip())
            if min_content_indent is None or indent < min_content_indent:
                min_content_indent = indent

    # Determine dedent amount: use minimum of fence and content indentation
    # This ensures we dedent by the fence baseline while preserving relative indentation
    if fence_indent is not None and min_content_indent is not None:
        dedent_amount = min(fence_indent, min_content_indent)
    elif fence_indent is not None:
        # If we only have fence markers (no content), use fence indentation
        dedent_amount = fence_indent
    elif min_content_indent is not None:
        # If we have content but no fences (shouldn't happen), use content indentation
        dedent_amount = min_content_indent
    else:
        # No fences or content found, use minimum indent like textwrap.dedent
        min_indent = None
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                if min_indent is None or indent < min_indent:
                    min_indent = indent
        dedent_amount = min_indent if min_indent is not None else 0

    # If no indentation found, return as-is
    if dedent_amount == 0:
        return content

    # Dedent all lines by dedent_amount
    dedented_lines = []
    for line in lines:
        if line.strip():
            # Remove dedent_amount spaces from the beginning
            if len(line) >= dedent_amount and line[:dedent_amount].strip() == "":
                dedented_lines.append(line[dedent_amount:])
            else:
                # Line has less than dedent_amount spaces, just strip leading whitespace
                dedented_lines.append(line.lstrip())
        else:
            # For blank lines, preserve up to dedent_amount spaces if they exist
            if len(line) >= dedent_amount:
                dedented_lines.append(line[dedent_amount:])
            else:
                dedented_lines.append(line)

    return "\n".join(dedented_lines)


def is_node_object(obj) -> bool:
    """Check if an object is a Node instance.

    Args:
        obj: The object to check

    Returns:
        True if obj is a Node instance, False otherwise

    Note: This function is kept for backwards compatibility but is no longer
    needed internally since all nodes are now Node objects.
    """
    return isinstance(obj, Node)


def dict_to_node(node_dict: NodeDict) -> Node:
    """Convert a dict to a Node object.

    Args:
        node_dict: The dict to convert

    Returns:
        A Node object (always returns a Node, never a dict)
    """
    content = node_dict.get("content", "")

    # Extract flags from node_dict (excluding content, indent, children)
    flags = {
        k: v for k, v in node_dict.items() if k not in ["content", "indent", "children"]
    }

    # Check content pattern first (before flag-based checks)
    # This ensures NumberedListNode and QuoteNode match before DetailsNode/ChoiceNode/PreserveListNode
    if NumberedListNode.matches(content, **flags):
        return NumberedListNode(
            content=content, indent=node_dict["indent"], children=node_dict["children"]
        )

    if QuoteNode.matches(content, **flags):
        return QuoteNode(
            content=content, indent=node_dict["indent"], children=node_dict["children"]
        )

    # Check flag-based node types before CodeFenceNode
    # This ensures nodes with special flags (preserve_list, details_block, type) take precedence
    # over code fence detection, since those nodes might contain code in their content

    # Check if this should be a PreserveListNode
    if PreserveListNode.matches(content, **flags):
        return PreserveListNode(
            content=content, indent=node_dict["indent"], children=node_dict["children"]
        )

    # Check if this should be a DetailsNode
    if DetailsNode.matches(content, **flags):
        return DetailsNode(
            content=content, indent=node_dict["indent"], children=node_dict["children"]
        )

    # Check if this should be a ChoiceNode
    if ChoiceNode.matches(content, **flags):
        return ChoiceNode(
            content=content, indent=node_dict["indent"], children=node_dict["children"]
        )

    # Check CodeFenceNode last (after flag-based checks)
    # This prevents code fences from overriding nodes with special flags
    if CodeFenceNode.matches(content, **flags):
        return CodeFenceNode(
            content=content, indent=node_dict["indent"], children=node_dict["children"]
        )

    # RegularNode is the final fallback (matches everything)
    return RegularNode(
        content=content, indent=node_dict["indent"], children=node_dict["children"]
    )


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
        - Handles code fences: content between ``` markers is always continuation
        - Normalizes indentation after collecting all lines for a bullet
    """
    bullet_groups = []
    current_indent = None
    current_content_lines = []
    in_code_fence = False

    for line in lines:
        if not line.strip():
            # Skip empty lines entirely (unless inside code fence)
            if in_code_fence and current_content_lines:
                current_content_lines.append(line)
            continue

        # Check if this line contains a fence marker
        stripped_content = line.strip()
        if stripped_content.startswith("```"):
            # Toggle fence state
            in_code_fence = not in_code_fence
            # This line is always a continuation
            if current_content_lines:
                current_content_lines.append(line)
            continue

        # If we're inside a code fence, always treat as continuation
        if in_code_fence:
            if current_content_lines:
                current_content_lines.append(line)
            continue

        # Calculate indentation
        indent = len(line) - len(line.lstrip())
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


def parse_roam_bullets(text: str) -> list[NodeDict]:
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

    Special handling for code fences: dedents fence content relative to
    the fence line itself, not the bullet marker minimum.

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

    # Normalize each continuation line, with special handling for code fences
    normalized_lines = [first_line]
    in_code_fence = False
    fence_base_indent = None
    first_content_indent = None  # Track first content line indent inside fence

    for line in continuation_lines:
        stripped = line.strip()

        # Check for fence markers
        if stripped.startswith("```"):
            if not in_code_fence:
                # Opening fence - record the base indent for this fence
                current_indent = len(line) - len(line.lstrip())
                fence_base_indent = current_indent
                first_content_indent = None  # Reset for new fence
            else:
                # Closing fence - reset first_content_indent
                first_content_indent = None
            in_code_fence = not in_code_fence

            # Process fence line normally
            if stripped:
                current_indent = len(line) - len(line.lstrip())
                new_indent = max(current_indent - bullet_indent, bullet_marker_len)
                normalized_lines.append(" " * new_indent + line.lstrip())
            else:
                normalized_lines.append(line)
        elif in_code_fence and fence_base_indent is not None:
            # Inside fence - calculate relative indent from fence base
            if stripped:
                current_indent = len(line) - len(line.lstrip())
                # Track first content line indent to establish baseline
                if first_content_indent is None:
                    first_content_indent = current_indent
                # Calculate relative indent from first content line
                # This preserves the indentation structure within the fence content
                relative_indent = current_indent - first_content_indent
                # Apply normalization: dedent by bullet indent, preserve relative structure
                # Adjust relative indent when first content is indented beyond fence
                if relative_indent > 0 and first_content_indent > fence_base_indent:
                    # Lines more indented than first content: reduce by 1 to compensate
                    # for the extra level of indentation when content doesn't align with fence
                    relative_indent -= 1
                new_indent = (first_content_indent - bullet_indent) + relative_indent
                normalized_lines.append(" " * new_indent + line.lstrip())
            else:
                # Blank lines inside fence - preserve relative to first content line
                if first_content_indent is not None:
                    # Calculate how many spaces the blank line should have based on first content
                    blank_line_indent = max(0, first_content_indent - bullet_indent)
                    normalized_lines.append(" " * blank_line_indent)
                else:
                    normalized_lines.append(line)
        else:
            # Regular continuation line
            if stripped:
                current_indent = len(line) - len(line.lstrip())
                new_indent = max(current_indent - bullet_indent, bullet_marker_len)
                normalized_lines.append(" " * new_indent + line.lstrip())
            else:
                normalized_lines.append(line)

    return "\n".join(normalized_lines)


def _find_parent(nodes: list[NodeDict], indent: int) -> NodeDict | None:
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


def transform_tree(nodes: list[NodeDict]) -> list[Node]:
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

        # Check if this is a code fence node - if so, convert it first and use modify()
        content = transformed_node["content"]
        has_code_fence = "```" in content

        if has_code_fence:
            # For code fences, we need to detect markers BEFORE creating the node
            # because markers like [details] affect which node type is created
            transformed_content = transformed_node["content"]

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

            # Update content after marker removal
            transformed_node["content"] = transformed_content

            # For code fences, create the node first to protect fence content
            # Then use modify() to apply transformations only to non-fence text
            node_obj = dict_to_node(transformed_node)

            # Define transformation function
            def apply_transformations(text: str) -> str:
                # Remove TODO/DONE markers
                text = re.sub(r"\{\{\[\[(DONE|TODO)\]\]\}\}\s*", "", text)
                # Convert :: labels to **label:** format
                text = _convert_double_colon_labels(text)
                return text

            # Apply transformations via modify() (protects fence content)
            node_obj = node_obj.modify(apply_transformations)

            result.append(node_obj)
        else:
            # For non-code-fence nodes, apply transformations normally
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

            # Convert to Node object if appropriate
            node_or_dict = dict_to_node(transformed_node)
            result.append(node_or_dict)

    return result


def _is_meta_node(node: NodeDict) -> bool:
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
    content = node.content.strip()
    return bool(re.match(r"^\d+\.\s", content))


def _format_numbered_list_item(node: Node) -> str:
    """Format a numbered list item with its children.

    Numbered list items should:
    - NOT have periods added (preserve as-is)
    - Children should be formatted and flattened
    - Return the item with newline(s) at the end for joining
    """
    content = node.content.strip()
    children = node.children

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


def _format_node(node: Node) -> str:
    """Format a single node using its __str__ method.

    Args:
        node: The node to format (Node object)

    Returns:
        Formatted string representation of the node
    """
    return str(node)


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
