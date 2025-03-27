import os
from io import StringIO
import json
from typing import Literal, List
from base64 import b64encode
from glob import glob

from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.operators.models import InferenceResult
from magic_pdf.operators.pipes import PipeResult
from magic_pdf.data.dataset import PymuDocDataset, ImageDataset
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


def process_file(
    pdf_bytes: bytes,
    file_type: Literal["pdf", "image"],
    image_writer: S3DataWriter | FileBasedDataWriter,
) -> tuple[InferenceResult, PipeResult]:

    if file_type == "pdf":
        ds = PymuDocDataset(pdf_bytes)
    else:
        ds = ImageDataset(pdf_bytes)

    infer_result: InferenceResult = None
    pipe_result: PipeResult = None

    if ds.classify() == SupportedPdfParseMethod.OCR:
        infer_result = ds.apply(
            doc_analyze, ocr=True, formula_enable=False, lang="german"
        )  # OCR language for paddlepaddle
        pipe_result = infer_result.pipe_ocr_mode(image_writer)
    else:
        infer_result = ds.apply(doc_analyze, ocr=False, formula_enable=False)
        pipe_result = infer_result.pipe_txt_mode(image_writer)

    return infer_result, pipe_result


def encode_image(image_path: str) -> str:
    """Encode image using base64."""
    with open(image_path, "rb") as f:
        return b64encode(f.read()).decode()


def process_files(file_paths: List[str], output_dir: str = "output_path") -> dict:
    """
    Process a list of PDF/image files and return a dictionary with all data.
    Each file will get its own subdirectory in `output_dir`.
    """
    # This will hold all processed results
    results_data = {"files": []}

    for file_path in file_paths:
        # Determine the file type
        if file_path.lower().endswith((".jpeg", ".jpg", ".png")):
            file_type = "image"
        elif file_path.lower().endswith(".pdf"):
            file_type = "pdf"
        else:
            raise Exception(f"File type not supported: {file_path}")

        # Prepare output paths
        file_basename = os.path.basename(file_path)
        current_output_dir = os.path.join(output_dir, file_basename)
        output_image_path = os.path.join(current_output_dir, "images")
        os.makedirs(output_image_path, exist_ok=True)

        # Read file bytes
        with open(file_path, "rb") as f:
            pdf_bytes = f.read()

        # Prepare writers
        writer = FileBasedDataWriter(current_output_dir)
        image_writer = FileBasedDataWriter(output_image_path)

        # Process the file
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

        # Save results (change to `if True:` or a more specific condition as needed)
        writer.write_string(
            f"{file_basename}_content_list.json", content_list_writer.get_value()
        )
        writer.write_string(f"{file_basename}.md", md_content)
        writer.write_string(
            f"{file_basename}_middle.json", middle_json_writer.get_value()
        )
        writer.write_string(
            f"{file_basename}_model.json",
            json.dumps(model_json, indent=4, ensure_ascii=False),
        )
        # Save visualizations
        pipe_result.draw_layout(
            os.path.join(current_output_dir, f"{file_basename}_layout.pdf")
        )
        pipe_result.draw_span(
            os.path.join(current_output_dir, f"{file_basename}_spans.pdf")
        )
        pipe_result.draw_line_sort(
            os.path.join(current_output_dir, f"{file_basename}_line_sort.pdf")
        )
        infer_result.draw_model(
            os.path.join(current_output_dir, f"{file_basename}_model.pdf")
        )

        # Create final data object for this file
        file_data = {}
        file_data["file"] = file_path
        file_data["layout"] = model_json
        file_data["info"] = middle_json
        file_data["content_list"] = content_list
        file_data["md_content"] = md_content

        # Encode images
        image_paths = glob(os.path.join(output_image_path, "*.jpg"))
        file_data["images"] = {
            os.path.basename(
                img_path
            ): f"data:image/jpeg;base64,{encode_image(img_path)}"
            for img_path in image_paths
        }

        # Collect per-file results
        results_data["files"].append(file_data)

    return results_data


if __name__ == "__main__":
    # Example usage:
    file_list = [
        "test_files/dokument_1.pdf",
        "test_files/dokument_12_scanned.jpeg",
        "test_files/dokument_13_scanned.pdf",
        "test_files/labor_04.pdf",
        "test_files/labor_7_scanned.jpeg",
        # Add more files as needed
    ]
    all_results = process_files(file_list, output_dir="output_path")

    # Write all data into a single JSON
    with open("output.json", "w") as f:
        json.dump(all_results, f, indent=4)
