"""Markdown assembly from processed page blocks."""

import html
from pathlib import Path
from typing import Any


class MarkdownGenerator:
    """Assemble structured page blocks into a flat Markdown document."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.images_dir = output_dir / "images"

    def image_markdown(self, relative_path: str) -> str:
        return f"![Image]({relative_path})"

    def table_markdown(self, html_content: str) -> str:
        """Convert PP-StructureV3 table HTML to a Markdown table snippet."""
        if not html_content:
            return ""
        import re

        lines = []
        html_content = html_content.strip()
        # Extract rows from the HTML table
        row_pattern = re.compile(r"<tr>(.*?)</tr>", re.DOTALL | re.IGNORECASE)
        cell_pattern = re.compile(r"<t[hd][^>]*>(.*?)</t[hd]>", re.DOTALL | re.IGNORECASE)

        rows = row_pattern.findall(html_content)
        for row_idx, row_html in enumerate(rows):
            cells = cell_pattern.findall(row_html)
            # Strip HTML tags inside cells, unescape
            cleaned = []
            for c in cells:
                text = re.sub(r"<[^>]+>", "", c).strip()
                text = html.unescape(text)
                cleaned.append(text)
            if row_idx == 1 and len(rows) > 1:
                # Second row → separator row
                lines.append("| " + " | ".join("---" for _ in cleaned) + " |")
            lines.append("| " + " | ".join(cleaned) + " |")

        # If only one row (header row only) → add separator
        if len(rows) == 1 and lines:
            header = lines[0]
            n_cols = header.count("|") - 1
            lines.insert(1, "| " + " | ".join("---" for _ in range(n_cols)) + " |")

        return "\n".join(lines)

    def assemble_page(
        self,
        page_num: int,
        blocks: list[dict[str, Any]],
        matched_images: dict[int, dict],
    ) -> str:
        """Convert one page's sorted OCR blocks + matched images to Markdown text.

        Parameters
        ----------
        page_num : int
            0-based page number.
        blocks : list[dict]
            OCR layout blocks in reading order.
        matched_images : dict[int -> dict]
            Mapping from OCR block index → pdf_image dict with keys
            "index", "ext", "image_bytes".

        Returns
        -------
        str
            Markdown for this page.
        """
        md_lines = []
        md_lines.append(f"<!-- Page {page_num + 1} -->\n")

        for idx, block in enumerate(blocks):
            typ = block.get("type", "text")
            content = block.get("content", "")
            orig_idx = block.get("_orig_idx", idx)

            if typ == "header":
                md_lines.append(f"# {content}\n")
            elif typ == "text":
                if content:
                    md_lines.append(f"{content}\n")
            elif typ == "table":
                table_md = self.table_markdown(content)
                if table_md:
                    md_lines.append(table_md + "\n")
            elif typ == "figure":
                matched = matched_images.get(orig_idx)
                if matched:
                    ext = matched.get("ext", "png")
                    img_bytes = matched["image_bytes"]
                    filename = f"page{page_num}_img{matched['index']}.{ext}"
                    img_path = self.images_dir / filename
                    img_path.write_bytes(img_bytes)
                    rel = Path("images") / filename
                    md_lines.append(self.image_markdown(rel.as_posix()) + "\n")
                else:
                    # No matched high-res image → write OCR alt text
                    if content:
                        md_lines.append(f"*{content}*\n")

        return "\n".join(md_lines)

    def write_output(self, pages_md: list[str]) -> str:
        """Concatenate all page Markdown and write to output.md.

        Returns
        -------
        str
            The full Markdown text.
        """
        full_md = "\n".join(pages_md)
        output_path = self.output_dir / "output.md"
        output_path.write_text(full_md, encoding="utf-8")
        return full_md
