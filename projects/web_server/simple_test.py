import os
from io import StringIO
import json
from base64 import b64encode
from glob import glob

from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.operators.models import InferenceResult
from magic_pdf.operators.pipes import PipeResult
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.config.enums import SupportedPdfParseMethod
from magic_pdf.data.data_reader_writer.s3 import S3DataReader, S3DataWriter
from magic_pdf.data.data_reader_writer import DataWriter, FileBasedDataWriter


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

def process_pdf(
    pdf_bytes: bytes,
    parse_method: str,
    image_writer: S3DataWriter | FileBasedDataWriter,
) -> tuple[InferenceResult, PipeResult]:
    """
    Process PDF file content

    Args:
        pdf_bytes: Binary content of PDF file
        parse_method: Parse method ('ocr', 'txt', 'auto')
        image_writer: Image writer

    Returns:
        Tuple[InferenceResult, PipeResult]: Returns inference result and pipeline result
    """
    ds = PymuDocDataset(pdf_bytes)
    infer_result: InferenceResult = None
    pipe_result: PipeResult = None

    if parse_method == "ocr":
        infer_result = ds.apply(doc_analyze, ocr=True)
        pipe_result = infer_result.pipe_ocr_mode(image_writer)
    elif parse_method == "txt":
        infer_result = ds.apply(doc_analyze, ocr=False)
        pipe_result = infer_result.pipe_txt_mode(image_writer)
    else:  # auto
        if ds.classify() == SupportedPdfParseMethod.OCR:
            infer_result = ds.apply(doc_analyze, ocr=True, formula_enable=False)
            pipe_result = infer_result.pipe_ocr_mode(image_writer)
        else:
            infer_result = ds.apply(doc_analyze, ocr=False, formula_enable=False)
            pipe_result = infer_result.pipe_txt_mode(image_writer)

    return infer_result, pipe_result


with open("small_ocr.pdf", "rb") as f:
    pdf_bytes = f.read()


output_dir = "output_path"

pdf_name = "small_ocr.pdf"
output_path = f"{output_dir}/{pdf_name}"
output_image_path = f"{output_path}/images"

writer = FileBasedDataWriter(output_path)
image_writer = FileBasedDataWriter(output_image_path)
os.makedirs(output_image_path, exist_ok=True)


infer_result, pipe_result = process_pdf(pdf_bytes, "auto", image_writer)

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
    writer.write_string(
        f"{pdf_name}_middle.json", middle_json_writer.get_value()
    )
    writer.write_string(
        f"{pdf_name}_model.json",
        json.dumps(model_json, indent=4, ensure_ascii=False),
    )
    # Save visualization results
    pipe_result.draw_layout(os.path.join(output_path, f"{pdf_name}_layout.pdf"))
    pipe_result.draw_span(os.path.join(output_path, f"{pdf_name}_spans.pdf"))
    pipe_result.draw_line_sort(
        os.path.join(output_path, f"{pdf_name}_line_sort.pdf")
    )
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
    os.path.basename(
        image_path
    ): f"data:image/jpeg;base64,{encode_image(image_path)}"
    for image_path in image_paths
}
data["md_content"] = md_content

with open("output.json", "w") as f:
    json.dump(data, f, indent=4)