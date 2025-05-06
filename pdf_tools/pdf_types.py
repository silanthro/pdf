from typing import Optional, Tuple, TypedDict


class PageContent(TypedDict):
    page: int
    content: str


class Edit(TypedDict):
    action: str
    page: int
    text: Optional[str]
    old_text: Optional[str]
    new_text: Optional[str]
    position: Optional[Tuple[float, float]]
    bbox: Optional[Tuple[float, float, float, float]]
    color: Optional[str]
    image_path: Optional[str]


class Annotation(TypedDict):
    page: int
    text: str
    bbox: Tuple[float, float, float, float]
    type: str


class Layout(TypedDict):
    page: int
    text: str
    bbox: tuple[int]
    font: str
    size: int
