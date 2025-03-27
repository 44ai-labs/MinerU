# file: app.py
from contextlib import asynccontextmanager

import os
import json
import uvicorn
import asyncio
import tempfile
from io import StringIO
from typing import Tuple, List

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

# ------------
# Your libraries
# ------------
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.operators.models import InferenceResult
from magic_pdf.operators.pipes import PipeResult
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.config.enums import SupportedPdfParseMethod
from magic_pdf.data.data_reader_writer.s3 import S3DataWriter
from magic_pdf.data.data_reader_writer import (
    DataWriter,
    FileBasedDataWriter,
)

from projects.web_server.server_types import MiddleJson, StructuredNode, StructuredNodeMetadata, UnstructuredMetadata


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model_lock = asyncio.Lock()
    yield


# -----------------------------------------------------------------------------
# 1) CREATE FASTAPI APP + STARTUP LOCK
# -----------------------------------------------------------------------------
app = FastAPI(lifespan=lifespan)


# -----------------------------------------------------------------------------
# 2) MEMORY WRITER (from your snippet)
# -----------------------------------------------------------------------------
class MemoryDataWriter(DataWriter):
    def __init__(self):
        self.buffer = StringIO()

    def write(self, path: str, data: bytes) -> None:
        if isinstance(data, str):
            self.buffer.write(data)
        else:
            self.buffer.write(data.decode("utf-8"))

    def write_string(self, path: str, data: str) -> None:
        self.buffer.write(data)

    def get_value(self) -> str:
        return self.buffer.getvalue()

    def close(self):
        self.buffer.close()


# -----------------------------------------------------------------------------
# 3) YOUR PROCESSING FUNCTION (from snippet)
# -----------------------------------------------------------------------------
def process_pdf(
    pdf_bytes: bytes,
    image_writer: S3DataWriter | FileBasedDataWriter,
) -> Tuple[InferenceResult, PipeResult]:
    """
    Process PDF file content.

    Args:
        pdf_bytes: Binary content of PDF file
        parse_method: Parse method ('ocr', 'txt', 'auto')
        image_writer: Image writer

    Returns:
        Tuple[InferenceResult, PipeResult]
    """
    ds = PymuDocDataset(pdf_bytes)
    infer_result = None
    pipe_result = None

    if ds.classify() == SupportedPdfParseMethod.OCR:
        infer_result = ds.apply(doc_analyze, ocr=True, formula_enable=False)
        pipe_result = infer_result.pipe_ocr_mode(image_writer)
    else:
        infer_result = ds.apply(doc_analyze, ocr=False, formula_enable=False)
        pipe_result = infer_result.pipe_txt_mode(image_writer)

    return infer_result, pipe_result



from typing import List

def middlejson_para_blocks_to_nodes(middle_json: MiddleJson) -> List[StructuredNode]:
    """
    For each page in middle_json.pdf_info:
      - Iterate over para_blocks.
      - Merge all lines (and spans) in that block into a single text string.
      - Create one StructuredNode per block.
    Returns a flat list of StructuredNode objects.
    """
    all_nodes: List[StructuredNode] = []

    for page_data in middle_json.pdf_info:
        page_idx = page_data.page_idx
        size = page_data.page_size  # e.g. [width, height]

        # Gather every "para_block" in this page
        for block in page_data.para_blocks:
            # Merge lines/spans
            block_lines = block.lines  # usually a list of Line
            line_texts = []
            for line in block_lines:
                # Each line can have multiple spans
                span_texts = [span.content for span in line.spans]
                # Join all spans in one line with a space, then strip
                single_line_str = " ".join(span_texts).strip()
                if single_line_str:
                    line_texts.append(single_line_str)

            # Merge all lines in the block with a newline (or space)
            block_text = "\n".join(line_texts).strip()

            # Collect metadata
            metadata_obj = UnstructuredMetadata(
                page_number=page_idx,
                block_type=block.type,
                bbox=block.bbox if block.bbox else None,
                page_width=size[0] if len(size) > 0 else None,
                page_height=size[1] if len(size) > 1 else None,
            )

            node_meta = StructuredNodeMetadata(
                unstructured_metadata=metadata_obj
            )

            node = StructuredNode(
                text=block_text,
                metadata=node_meta
            )
            all_nodes.append(node)

    return all_nodes



# -----------------------------------------------------------------------------
# 4) ENDPOINT: EXTRACT _middle.json
# -----------------------------------------------------------------------------
@app.post("/analyze-file", response_model=StructuredNode)
async def extract_middle_file(
    file: UploadFile = File(...),
) -> StructuredNode:
    """
    Accepts a PDF file upload, processes it (one at a time),
    and returns the _middle.json content. Temporary files are
    used/removed automatically.
    """

    # Read PDF bytes from request
    pdf_bytes = await file.read()

    # Acquire lock so only one request uses the model at a time
    async with app.state.model_lock:
        # Create a temporary directory for any images or intermediate artifacts
        with tempfile.TemporaryDirectory() as tmpdir:
            # In your snippet, you store images in output_image_path
            output_image_path = os.path.join(tmpdir, "images")
            os.makedirs(output_image_path, exist_ok=True)
            image_writer = FileBasedDataWriter(output_image_path)

            # Run your pipeline
            infer_result, pipe_result = process_pdf(pdf_bytes, image_writer)

            # Dump the _middle.json into memory
            middle_json_writer = MemoryDataWriter()
            pipe_result.dump_middle_json(middle_json_writer, "")
            middle_json_str = middle_json_writer.get_value()
            middle_json = json.loads(middle_json_str)

    # Once we exit the `with tempfile.TemporaryDirectory()`, all files are removed
    # Once we exit the `async with app.state.model_lock`, the lock is released

    # Return the middle_json as the response

    typed_middle = MiddleJson(**middle_json)
    # return typed_middle
    with open("middle.json", "w") as f:
        f.write(json.dumps(middle_json, indent=2))
    structured_nodes = middlejson_para_blocks_to_nodes(typed_middle)
    return structured_nodes



# -----------------------------------------------------------------------------
# 5) LAUNCH (if run directly)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Run with a single worker so the lock effectively ensures single concurrency
    uvicorn.run(app, host="0.0.0.0", port=4419)
