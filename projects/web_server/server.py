# file: app.py
from contextlib import asynccontextmanager

import os
import json
import uvicorn
import asyncio
import tempfile
from io import StringIO
from typing import Tuple

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


# -----------------------------------------------------------------------------
# 4) ENDPOINT: EXTRACT _middle.json
# -----------------------------------------------------------------------------
@app.post("/analyze-file")
async def extract_middle_file(
    file: UploadFile = File(...),
):
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
    return JSONResponse(content=middle_json)


# -----------------------------------------------------------------------------
# 5) LAUNCH (if run directly)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Run with a single worker so the lock effectively ensures single concurrency
    uvicorn.run(app, host="0.0.0.0", port=4419)
