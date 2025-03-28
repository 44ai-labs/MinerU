from typing import List, Optional, Union
from pydantic import BaseModel, Field

from typing import List, Optional, Union, Any
from pydantic import BaseModel


class Span(BaseModel):
    bbox: List[float]  # [left, top, right, bottom]
    score: Optional[float] = None  # might be missing
    content: Optional[str] = None
    html: Optional[str] = None
    type: str
    image_path: Optional[str] = None


class Line(BaseModel):
    bbox: List[float]
    spans: List[Span]
    index: Optional[int] = None


class TableBlock(BaseModel):
    type: str
    bbox: List[float]
    group_id: Optional[int] = None
    lines: Optional[List[Line]] = None
    index: Optional[float] = None
    virtual_lines: Optional[List[Any]] = None


class ParsedTable(BaseModel):
    type: str
    bbox: List[float]
    blocks: List[TableBlock]
    index: Optional[float] = None
    page_num: Optional[str] = None
    page_size: Optional[List[float]] = None


class DiscardedBlock(BaseModel):
    type: str
    bbox: List[float]
    lines: Optional[List[Line]] = None


class PreprocBlockLine(BaseModel):
    bbox: List[int]
    spans: List[Span]
    index: Optional[Union[int, float]] = None


class PreprocBlock(BaseModel):
    type: str
    bbox: List[int]
    lines: Optional[List[PreprocBlockLine]] = None
    index: Optional[Union[int, float]] = None
    page_num: Optional[str] = None
    page_size: Optional[List[float]] = None
    bbox_fs: Optional[List[int]] = None


class PdfInfo(BaseModel):
    preproc_blocks: List[PreprocBlock]
    layout_bboxes: List[List[float]] = []
    page_idx: int
    page_size: List[float]
    _layout_tree: List[Any] = []
    images: List[Any] = []
    tables: List[ParsedTable] = []
    interline_equations: List[Any] = []
    discarded_blocks: List[DiscardedBlock] = []
    need_drop: Optional[bool] = None
    drop_reason: List[str] = []
    para_blocks: List[PreprocBlock]


class LayoutDet(BaseModel):
    category_id: int
    poly: List[Union[int, float]]
    score: float
    html: Optional[str] = None
    text: Optional[str] = None


class PageInfo(BaseModel):
    page_no: int
    width: int
    height: int


class Layout(BaseModel):
    layout_dets: List[LayoutDet]
    page_info: PageInfo


class Info(BaseModel):
    pdf_info: List[PdfInfo]
    _parse_type: Optional[str] = None
    _version_name: Optional[str] = None


class ContentItem(BaseModel):
    type: str
    text: Optional[str] = None
    page_idx: int
    text_level: Optional[int] = None
    img_path: Optional[str] = None
    table_caption: Optional[List[str]] = None
    table_footnote: Optional[List[str]] = None
    table_body: Optional[str] = None


class MinerUReturn(BaseModel):
    file: Optional[str] = None
    layout: List[Layout]
    info: Info
    content_list: List[ContentItem]
    md_content: Optional[str] = None
