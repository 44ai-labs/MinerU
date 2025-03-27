# file: test_client.py
import requests

def test_extract_middle_json(pdf_path):
    url = "http://127.0.0.1:4419/analyze-file"
    
    # 'file' is the field name expected by the FastAPI endpoint.
    files = {
        "file": (pdf_path, open(pdf_path, "rb"), "application/pdf"),
    }
    
    response = requests.post(url, files=files)
    
    if response.status_code == 200:
        print("Successfully got response:")
        print(response.json())
    else:
        print("Error:", response.status_code)
        print(response.text)

if __name__ == "__main__":
    # Provide path to a local PDF
    path_to_pdf = "small_ocr.pdf"
    test_extract_middle_json(path_to_pdf)
