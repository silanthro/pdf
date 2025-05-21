import shutil
import tempfile
from typing import List, Optional, Tuple, Union

import fitz

from .utils import path_is_allowed


def _save_pdf(doc, path: str):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_path = tmp_file.name
    doc.save(tmp_path, incremental=False)
    shutil.move(tmp_path, path)


def add_text(
    path: str,
    text: str,
    position: Tuple[float, float],
    pages: Optional[List[int]] = None,
):
    """
    Adds text at a specified position on one or more PDF pages.

    Args:
        path (str): Path to the PDF file.
        text (str): The text to insert.
        position (Tuple[float, float]): (x, y) coordinates in PDF units.
        pages (list[int], optional): Pages to apply the text to, zero-indexed. Defaults to all pages.
    """
    path_is_allowed(path)
    doc = fitz.open(path)
    pages = pages or list(range(len(doc)))
    for p in pages:
        page = doc[p]
        page.insert_text(position, text)
    doc.save(path, incremental=True)
    doc.close()


FONT_FALLBACKS = {
    "Times New Roman": "Times-Roman",
    "Times": "Times-Roman",
    "Arial": "helv",
    "Arial Bold": "helv",
    "Helvetica": "helv",
    "Courier": "courier",
    "Courier New": "courier",
    "Symbol": "symbol",
    # fallback
    "default": "helv",
}


def parse_fontname(font_name: str) -> str:
    for key in FONT_FALLBACKS:
        if key.lower() in font_name.lower():
            return FONT_FALLBACKS[key]
    return FONT_FALLBACKS["default"]


def parse_fontcolor(value: Union[int, float]) -> Tuple[float, float, float]:
    if isinstance(value, float):
        # Already normalized
        return (value, value, value)
    if isinstance(value, int):
        r = ((value >> 16) & 255) / 255
        g = ((value >> 8) & 255) / 255
        b = (value & 255) / 255
        return (r, g, b)
    return (0, 0, 0)


def replace_text(
    path: str, old_text: str, new_text: str, pages: Optional[List[int]] = None
):
    """
    Replaces all instances of `old_text` with `new_text` on specified PDF pages.
    If `new_text` is an empty string, `old_text` will be redacted without replacement.

    Notes:
    - Text matching is case-sensitive and whitespace-sensitive.

    Args:
        path (str): Path to the PDF file to modify.
        old_text (str): Exact text string to search for and replace.
        new_text (str): Replacement text to insert at each found location.
        pages (list[int], optional): List of 0-based page indices to operate on.
                                     If None, all pages will be scanned.

    Raises:
        ValueError: If the replacement font is not compatible or the file can't be saved.
    """
    path_is_allowed(path)
    doc = fitz.open(path)
    pages = pages or list(range(len(doc)))

    for p in pages:
        page = doc[p]
        text_instances = page.search_for(old_text)

        # Capture all spans up front
        all_spans = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    all_spans.append(span)

        # Match each found bbox to its closest span
        replacements = []
        for inst in text_instances:
            matching_spans = [
                span
                for span in all_spans
                if old_text in span["text"] and fitz.Rect(span["bbox"]).intersects(inst)
            ]
            if matching_spans:
                best_span = matching_spans[0]
                replacements.append(
                    {
                        "bbox": inst,
                        "font": best_span["font"],
                        "size": best_span["size"],
                        "origin": best_span["origin"],
                    }
                )

        # Redact all at once
        for r in replacements:
            page.add_redact_annot(r["bbox"], fill=(1, 1, 1))
        page.apply_redactions()

        # Insert new text
        for r in replacements:
            page.insert_text(
                (r["bbox"].x0, r["origin"][1]),
                new_text,
                fontname=parse_fontname(r["font"]),
                fontsize=r["size"],
                color=parse_fontcolor(span.get("color", 0)),
            )

    # Save to a temp file then overwrite
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_path = tmp_file.name
    doc.save(tmp_path, incremental=False)
    shutil.move(tmp_path, path)
    doc.close()


def highlight_text(path: str, text: str, pages: Optional[List[int]] = None):
    """
    Highlights all instances of a given string on one or more PDF pages.

    Args:
        path (str): Path to the PDF file.
        text (str): The exact text to highlight.
        pages (list[int], optional): Pages to search, zero-indexed. Defaults to all pages.
    """
    path_is_allowed(path)
    doc = fitz.open(path)
    pages = pages or list(range(len(doc)))
    for p in pages:
        page = doc[p]
        for inst in page.search_for(text):
            page.add_highlight_annot(inst)
    _save_pdf(doc, path)
    doc.close()


def insert_image(
    path: str,
    image_path: str,
    position: Tuple[float, float],
    size: Optional[Tuple[float, float]] = None,
    pages: Optional[List[int]] = None,
):
    """
    Inserts an image at the specified position on one or more PDF pages.

    Args:
        path (str): Path to the PDF file.
        image_path (str): Path to the image file (e.g., PNG, JPEG).
        position (Tuple[float, float]): (x, y) coordinates in PDF units.
        size (Tuple[float, float]): (width, height) in PDF points. Defaults to (100, 100)
        pages (list[int], optional): Pages to insert the image into, zero-indexed. Defaults to all pages.
    """
    path_is_allowed(path)
    doc = fitz.open(path)
    pages = pages or list(range(len(doc)))
    img = open(image_path, "rb").read()
    for p in pages:
        page = doc[p]
        rect = fitz.Rect(
            position[0], position[1], position[0] + size[0], position[1] + size[1]
        )
        page.insert_image(rect, stream=img)
    _save_pdf(doc, path)
    doc.close()


def delete_text_by_bbox(
    path: str,
    bbox: Tuple[float, float, float, float],
    pages: Optional[List[int]] = None,
):
    """
    Redacts (deletes) all content within a bounding box on specified pages.

    Args:
        path (str): Path to the PDF file.
        bbox (Tuple[float, float, float, float]): Rectangle (x0, y0, x1, y1) to redact.
        pages (list[int], optional): Pages to apply the redaction to, zero-indexed. Defaults to all pages.
    """
    path_is_allowed(path)
    doc = fitz.open(path)
    pages = pages or list(range(len(doc)))
    rect = fitz.Rect(*bbox)
    for p in pages:
        page = doc[p]
        page.add_redact_annot(rect, fill=(1, 1, 1))
        page.apply_redactions()
    _save_pdf(doc, path)
    doc.close()


def annotate_rect(
    path: str,
    bbox: Tuple[float, float, float, float],
    color: str,
    pages: Optional[List[int]] = None,
):
    """
    Draws a rectangle annotation over the given bounding box on specified pages.

    Args:
        path (str): Path to the PDF file.
        bbox (Tuple[float, float, float, float]): Rectangle (x0, y0, x1, y1) in PDF coordinates.
        color (str): Hex string representing the RGB color (e.g., "#FF0000").
        pages (list[int], optional): Pages to apply the annotation to, zero-indexed. Defaults to all pages.
    """
    path_is_allowed(path)
    doc = fitz.open(path)
    pages = pages or list(range(len(doc)))
    rect = fitz.Rect(*bbox)
    rgb_color = tuple(int(color.lstrip("#")[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    for p in pages:
        page = doc[p]
        page.draw_rect(rect, color=rgb_color, fill=None)
    doc.save(path, incremental=True)
    doc.close()
