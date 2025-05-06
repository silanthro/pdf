import statistics
from typing import List, Optional

import fitz

from .pdf_types import Annotation, Layout, PageContent
from .utils import path_is_allowed


def get_metadata(path: str) -> dict:
    """
    Retrieves metadata for a PDF file, including page count, title, author, creation and modification dates.

    Args:
        path (str): Path to the PDF file.

    Returns:
        dict: A dictionary with metadata keys like 'title', 'author', 'creationDate', 'modDate', 'producer', and 'page_count'.
    """
    path_is_allowed(path)
    doc = fitz.open(path)
    metadata = doc.metadata
    metadata["page_count"] = doc.page_count
    doc.close()
    return metadata


def extract_content_as_text(
    path: str, pages: Optional[List[int]] = None
) -> list[PageContent]:
    """
    Extracts plain text from a PDF file.

    Args:
        path (str): Path to the PDF file.
        pages (list[int], optional): Specific pages to extract, zero-indexed. If None, extracts all pages.

    Returns:
        list[PageContent]: List of PageContent objects, where each object has the following keys
            - page (int): Page number
            - content (str): Text content
    """
    path_is_allowed(path)
    doc = fitz.open(path)
    pages = pages or list(range(len(doc)))
    content = []
    for page in pages:
        content.append(
            PageContent(
                page=page,
                content=doc[page].get_text(),
            )
        )
    doc.close()
    return content


def extract_content_as_json(path: str, pages: Optional[List[int]] = None) -> list:
    """
    Extracts structured content (blocks and layout) from specified pages in JSON format.

    Args:
        path (str): Path to the PDF file.
        pages (list[int], optional): Specific pages to extract, zero-indexed. If None, extracts all pages.

    Returns:
        list[dict]: List of page-level dictionaries with 'page' and 'blocks' keys.
    """
    path_is_allowed(path)
    doc = fitz.open(path)
    pages = pages or list(range(len(doc)))
    result = []
    for p in pages:
        blocks = doc[p].get_text("dict")["blocks"]
        result.append({"page": p, "blocks": blocks})
    doc.close()
    return result


def extract_content_as_markdown(
    path: str, page: Optional[List[int]] = None
) -> list[PageContent]:
    """
    Extracts text content from a PDF and formats it as Markdown.
    Groups lines into paragraphs, formats bold/italic text, infers headings, and converts detected tables.

    Args:
        path (str): Path to the PDF file.
        pages (list[int], optional): Specific pages to extract, zero-indexed. If None, extracts all pages.

    Returns:
        list[PageContent]: List of PageContent objects, where each object has the following keys
            - page (int): Page number
            - content (str): Markdown content
    """
    path_is_allowed(path)

    def format_span(text, is_bold, is_italic):
        if is_bold and is_italic:
            return f"***{text}***"
        elif is_bold:
            return f"**{text}**"
        elif is_italic:
            return f"*{text}*"
        return text

    doc = fitz.open(path)
    pages = page or list(range(len(doc)))

    output = []

    for p in pages:
        page_content = []

        page = doc[p]
        blocks = page.get_text("dict")["blocks"]

        spans_by_line = []
        for block in blocks:
            for line in block.get("lines", []):
                line_text = ""
                line_styles = []
                for span in line["spans"]:
                    span_text = span["text"].strip()
                    if not span_text:
                        continue
                    is_bold = "Bold" in span["font"]
                    is_italic = "Italic" in span["font"] or "Oblique" in span["font"]
                    line_styles.append(span["size"])
                    formatted = format_span(span_text, is_bold, is_italic)
                    line_text += formatted + " "
                if line_text.strip():
                    spans_by_line.append(
                        {
                            "text": line_text.strip(),
                            "top": line["bbox"][1],
                            "size": statistics.median(line_styles)
                            if line_styles
                            else 12,
                        }
                    )

        if spans_by_line:
            normal_size = statistics.median([line["size"] for line in spans_by_line])
        else:
            normal_size = 12

        # Group lines into paragraphs by vertical proximity
        grouped_paragraphs = []
        current_para = []
        prev_top = None
        for line in spans_by_line:
            if prev_top is not None and abs(line["top"] - prev_top) > 15:
                grouped_paragraphs.append(current_para)
                current_para = []
            current_para.append(line)
            prev_top = line["top"]
        if current_para:
            grouped_paragraphs.append(current_para)

        for para in grouped_paragraphs:
            if not para:
                continue
            first_line = para[0]
            heading = ""
            if first_line["size"] > normal_size * 1.5:
                heading = "# "
            elif first_line["size"] > normal_size * 1.2:
                heading = "## "
            elif first_line["size"] > normal_size * 1.1:
                heading = "### "

            para_text = " ".join(line["text"] for line in para)
            page_content.append(f"{heading}{para_text}\n")

        # Attempt to detect tables using 'table' extractor
        try:
            tables = page.find_tables()
            for table in tables:
                page_content.append("\n")
                for i, row in enumerate(table.extract()):
                    line = " | ".join(cell.strip() for cell in row)
                    if i == 0:
                        separator = " | ".join(["---"] * len(row))
                        page_content.append(f"| {line} |")
                        page_content.append(f"| {separator} |")
                    else:
                        page_content.append(f"| {line} |")
                page_content.append("\n")
        except Exception:
            pass

        output.append(
            PageContent(
                page=p,
                content="\n".join(page_content),
            )
        )

    doc.close()
    return output


def extract_text_with_layout(
    path: str, pages: Optional[List[int]] = None
) -> list[Layout]:
    """
    Extracts text with font, size, and position (bounding box) data for precise layout-aware tasks.

    Args:
        path (str): Path to the PDF file.
        pages (list[int], optional): Specific pages to extract, zero-indexed. If None, extracts all pages.

    Returns:
        list[dict]: Each dict contains 'page', 'text', 'bbox', 'font', and 'size' fields.
    """
    path_is_allowed(path)
    doc = fitz.open(path)
    pages = pages or list(range(len(doc)))
    results = []
    for p in pages:
        blocks = doc[p].get_text("dict")["blocks"]
        for block in blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    results.append(
                        Layout(
                            page=p,
                            text=span["text"],
                            bbox=span["bbox"],
                            font=span["font"],
                            size=span["size"],
                        )
                    )
    doc.close()
    return results


def list_annotations(path: str, pages: Optional[List[int]] = None) -> list[Annotation]:
    """
    Lists annotations present in the specified PDF pages.

    Args:
        path (str): Path to the PDF file.
        pages (list[int], optional): Specific pages to inspect, zero-indexed. If None, checks all pages.

    Returns:
        List[Annotation]: A list of annotations with page number, text, bbox, and type.
    """
    path_is_allowed(path)
    doc = fitz.open(path)
    pages = pages or list(range(len(doc)))
    annotations = []
    for p in pages:
        for annot in doc[p].annots() or []:
            annotations.append(
                Annotation(
                    page=p,
                    text=annot.info.get("content", ""),
                    bbox=annot.rect,
                    type=annot.type[1],
                )
            )
    doc.close()
    return annotations
