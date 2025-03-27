from typing import List, Optional, Union
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Lowest-level: a single "span" on a line
# -----------------------------------------------------------------------------
class Span(BaseModel):
    bbox: List[float]
    score: float
    content: str
    type: str


# -----------------------------------------------------------------------------
# Next level: each "line" has a bbox, spans[], etc.
# -----------------------------------------------------------------------------
class Line(BaseModel):
    bbox: List[float]
    spans: List[Span]
    index: Optional[int] = None
    # Some lines in your data had "cross_page": true, so you can add:
    # cross_page: Optional[bool] = None


# -----------------------------------------------------------------------------
# A "block" under preproc_blocks or para_blocks, e.g. type=="text"
# -----------------------------------------------------------------------------
class PreprocBlock(BaseModel):
    type: str
    bbox: List[float]
    # lines can be empty or omitted, so we allow an empty list as default
    lines: List[Line] = Field(default_factory=list)

    # index can be float (e.g. 7.5) or int
    index: Optional[Union[float, int]] = None

    # Some optional fields that appear in para_blocks or text blocks
    page_num: Optional[str] = None
    page_size: Optional[List[float]] = None
    bbox_fs: Optional[List[float]] = None
    lines_deleted: Optional[bool] = None


# -----------------------------------------------------------------------------
# Discarded blocks have a "type":"discarded", a bbox, lines...
# -----------------------------------------------------------------------------
class DiscardedBlock(BaseModel):
    type: str
    bbox: List[float]
    lines: List[Line] = Field(default_factory=list)


# -----------------------------------------------------------------------------
# "para_blocks" can have the same shape as PreprocBlock
# (including lines, index, etc.)
# -----------------------------------------------------------------------------
class ParaBlock(PreprocBlock):
    pass


# -----------------------------------------------------------------------------
# The pdf_info[] list, each item has preproc_blocks, page_idx, etc.
# -----------------------------------------------------------------------------
class PdfInfo(BaseModel):
    preproc_blocks: List[PreprocBlock]
    layout_bboxes: List = Field(default_factory=list)
    page_idx: int
    page_size: List[float]

    # The original JSON uses an underscore name, so use alias:
    layout_tree: List = Field(default_factory=list, alias="_layout_tree")

    images: List = Field(default_factory=list)
    tables: List = Field(default_factory=list)
    interline_equations: List = Field(default_factory=list)
    discarded_blocks: List[DiscardedBlock] = Field(default_factory=list)

    need_drop: bool
    drop_reason: List = Field(default_factory=list)

    para_blocks: List[ParaBlock] = Field(default_factory=list)


# -----------------------------------------------------------------------------
# The top-level object, with "pdf_info" and also _parse_type, _version_name
# -----------------------------------------------------------------------------
class MiddleJson(BaseModel):
    pdf_info: List[PdfInfo]

    # Original JSON fields had leading underscores, so alias them:
    parse_type: Optional[str] = Field(alias="_parse_type")
    version_name: Optional[str] = Field(alias="_version_name")


# -----------------------------------------------------------------------------
# Output types
# -----------------------------------------------------------------------------


class UnstructuredMetadata(BaseModel):
    """
    Represents the data you build up in `metadata` (like category, page_width, etc.).
    """

    category: Optional[str] = None
    page_height: Optional[float] = None
    page_width: Optional[float] = None
    # Each bbox coordinate is [x, y], so store it as a list of lists
    bbox: Optional[List[List[float]]] = None
    page_number: Optional[int] = None
    table_markdown: Optional[str] = None


class StructuredNodeMetadata(BaseModel):
    """
    Represents the `metadata` field on StructuredNode, which itself
    has a sub-field called `unstructured_metadata`.
    """

    unstructured_metadata: UnstructuredMetadata


class StructuredNode(BaseModel):
    """
    The main node model with `text` and a `metadata` dict that wraps
    `unstructured_metadata`.
    """

    text: str
    metadata: StructuredNodeMetadata
