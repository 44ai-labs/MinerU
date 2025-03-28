# file: app.py
from contextlib import asynccontextmanager

import os
import json
import uvicorn
import asyncio
import tempfile
from io import StringIO
from typing import Tuple, List, Literal
from base64 import b64encode
from glob import glob

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

# ------------
# Your libraries
# ------------
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.operators.models import InferenceResult
from magic_pdf.operators.pipes import PipeResult
from magic_pdf.data.dataset import PymuDocDataset, ImageDataset
from magic_pdf.config.enums import SupportedPdfParseMethod
from magic_pdf.data.data_reader_writer.s3 import S3DataWriter
from magic_pdf.data.data_reader_writer import (
    DataWriter,
    FileBasedDataWriter,
)

from projects.web_server.server_types import (
    MinerUReturn
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
def process_file(
    pdf_bytes: bytes,
    file_type: Literal["pdf", "image"],
    image_writer: S3DataWriter | FileBasedDataWriter,
) -> Tuple[InferenceResult, PipeResult]:

    if file_type == "pdf":
        ds = PymuDocDataset(pdf_bytes)
    else:
        ds = ImageDataset(pdf_bytes)

    infer_result: InferenceResult = None
    pipe_result: PipeResult = None

    if ds.classify() == SupportedPdfParseMethod.OCR:
        infer_result = ds.apply(doc_analyze, ocr=True, formula_enable=False)
        pipe_result = infer_result.pipe_ocr_mode(image_writer)
    else:
        infer_result = ds.apply(doc_analyze, ocr=False, formula_enable=False)
        pipe_result = infer_result.pipe_txt_mode(image_writer)

    return infer_result, pipe_result


def encode_image(image_path: str) -> str:
    """Encode image using base64."""
    with open(image_path, "rb") as f:
        return b64encode(f.read()).decode()


# -----------------------------------------------------------------------------
# 4) ENDPOINT: EXTRACT _middle.json
# -----------------------------------------------------------------------------
@app.post("/analyze-file", response_model=MinerUReturn)
async def extract_middle_file(
    file: UploadFile = File(...),
) -> MinerUReturn:
    """
    Accepts a PDF file upload, processes it (one at a time),
    and returns the _middle.json content. Temporary files are
    used/removed automatically.
    """

    # Read PDF bytes from request
    pdf_bytes = await file.read()

    # Check file extension
    filename = file.filename.lower()
    if filename.endswith((".jpeg", ".jpg", ".png")):
        file_type = "image"
    elif filename.endswith(".pdf"):
        file_type = "pdf"
    else:
        raise HTTPException(
            status_code=400, detail=f"File type not supported: {filename}"
        )

    # Acquire lock so only one request uses the model at a time
    async with app.state.model_lock:
        # Create a temporary directory for any images or intermediate artifacts
        with tempfile.TemporaryDirectory() as tmpdir:
            # In your snippet, you store images in output_image_path
            output_image_path = os.path.join(tmpdir, "images")
            os.makedirs(output_image_path, exist_ok=True)
            image_writer = FileBasedDataWriter(output_image_path)

            # Run your pipeline
            infer_result, pipe_result = process_file(pdf_bytes, file_type, image_writer)

            # Memory writers to capture content
            content_list_writer = MemoryDataWriter()
            md_content_writer = MemoryDataWriter()
            middle_json_writer = MemoryDataWriter()

            # Dump textual results
            pipe_result.dump_content_list(content_list_writer, "", "images")
            pipe_result.dump_md(md_content_writer, "", "images")
            pipe_result.dump_middle_json(middle_json_writer, "")

            content_list = json.loads(content_list_writer.get_value())
            md_content = md_content_writer.get_value()
            middle_json = json.loads(middle_json_writer.get_value())
            model_json = infer_result.get_infer_res()

            # Create final data object for this file
            file_data = {}
            file_data["layout"] = model_json
            file_data["info"] = middle_json
            file_data["content_list"] = content_list
            file_data["md_content"] = md_content

            # Encode images
            # image_paths = glob(os.path.join(output_image_path, "*.jpg"))
            # file_data["images"] = {
            #     os.path.basename(
            #         img_path
            #     ): f"data:image/jpeg;base64,{encode_image(img_path)}"
            #     for img_path in image_paths
            # }

    # Once we exit the `with tempfile.TemporaryDirectory()`, all files are removed
    # Once we exit the `async with app.state.model_lock`, the lock is released

    # Return the middle_json as the response

    typed_return = MinerUReturn(**file_data)
    return typed_return


# -----------------------------------------------------------------------------
# 5) LAUNCH (if run directly)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Run with a single worker so the lock effectively ensures single concurrency
    uvicorn.run(app, host="0.0.0.0", port=4419)
