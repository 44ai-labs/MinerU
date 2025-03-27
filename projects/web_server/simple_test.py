import os
from io import StringIO
import json
from typing import Literal
from base64 import b64encode
from glob import glob

from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.operators.models import InferenceResult
from magic_pdf.operators.pipes import PipeResult
from magic_pdf.data.dataset import PymuDocDataset, ImageDataset
from magic_pdf.config.enums import SupportedPdfParseMethod
from magic_pdf.data.data_reader_writer.s3 import S3DataReader, S3DataWriter
from magic_pdf.data.data_reader_writer import DataWriter, FileBasedDataWriter

PDF_PATH = "test_files/dokument_1.pdf"
PDF_PATH = "test_files/dokument_12_scanned.jpeg"


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


def process_file(
    pdf_bytes: bytes,
    type: Literal["pdf", "image"],
    image_writer: S3DataWriter | FileBasedDataWriter,
) -> tuple[InferenceResult, PipeResult]:

    if type == "pdf":
        ds = PymuDocDataset(pdf_bytes)
    else:
        ds = ImageDataset(pdf_bytes)
    infer_result: InferenceResult = None
    pipe_result: PipeResult = None

    if ds.classify() == SupportedPdfParseMethod.OCR:
        infer_result = ds.apply(
            doc_analyze, ocr=True, formula_enable=False, lang="german"
        )  # ocr language for paddlepaddle
        pipe_result = infer_result.pipe_ocr_mode(image_writer)
    else:
        infer_result = ds.apply(doc_analyze, ocr=False, formula_enable=False)
        pipe_result = infer_result.pipe_txt_mode(image_writer)

    return infer_result, pipe_result


with open(PDF_PATH, "rb") as f:
    pdf_bytes = f.read()


output_dir = "output_path"

pdf_name = PDF_PATH
output_path = f"{output_dir}/{pdf_name}"
output_image_path = f"{output_path}/images"

writer = FileBasedDataWriter(output_path)
image_writer = FileBasedDataWriter(output_image_path)
os.makedirs(output_image_path, exist_ok=True)

file_type = "pdf"
if PDF_PATH.endswith(".jpeg") or PDF_PATH.endswith(".jpg") or PDF_PATH.endswith(".png"):
    file_type = "image"
else:
    if not PDF_PATH.endswith(".pdf"):
        raise Exception("File type not supported")


infer_result, pipe_result = process_file(pdf_bytes, file_type, image_writer)

content_list_writer = MemoryDataWriter()
md_content_writer = MemoryDataWriter()
middle_json_writer = MemoryDataWriter()

# Use PipeResult's dump method to get data
pipe_result.dump_content_list(content_list_writer, "", "images")
pipe_result.dump_md(md_content_writer, "", "images")
pipe_result.dump_middle_json(middle_json_writer, "")

# Get content
content_list = json.loads(content_list_writer.get_value())
md_content = md_content_writer.get_value()
middle_json = json.loads(middle_json_writer.get_value())
model_json = infer_result.get_infer_res()

# If results need to be saved
if True:
    writer.write_string(
        f"{pdf_name}_content_list.json", content_list_writer.get_value()
    )
    writer.write_string(f"{pdf_name}.md", md_content)
    writer.write_string(f"{pdf_name}_middle.json", middle_json_writer.get_value())
    writer.write_string(
        f"{pdf_name}_model.json",
        json.dumps(model_json, indent=4, ensure_ascii=False),
    )
    # Save visualization results
    pipe_result.draw_layout(os.path.join(output_path, f"{pdf_name}_layout.pdf"))
    pipe_result.draw_span(os.path.join(output_path, f"{pdf_name}_spans.pdf"))
    pipe_result.draw_line_sort(os.path.join(output_path, f"{pdf_name}_line_sort.pdf"))
    infer_result.draw_model(os.path.join(output_path, f"{pdf_name}_model.pdf"))


def encode_image(image_path: str) -> str:
    """Encode image using base64"""
    with open(image_path, "rb") as f:
        return b64encode(f.read()).decode()


data = {}
data["layout"] = model_json
data["info"] = middle_json
data["content_list"] = content_list
image_paths = glob(f"{output_image_path}/*.jpg")
data["images"] = {
    os.path.basename(image_path): f"data:image/jpeg;base64,{encode_image(image_path)}"
    for image_path in image_paths
}
data["md_content"] = md_content

with open("output.json", "w") as f:
    json.dump(data, f, indent=4)
