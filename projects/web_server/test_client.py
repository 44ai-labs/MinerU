# file: test_client_async.py
import asyncio
import httpx


async def test_extract_middle_json(client: httpx.AsyncClient, pdf_path: str) -> bool:
    url = "http://127.0.0.1:4419/analyze-file"

    # Read file in binary
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # Prepare the 'files' dict expected by the FastAPI endpoint
    files = {
        "file": (pdf_path, pdf_bytes, "application/pdf"),
    }

    # Make the async request
    response = await client.post(url, files=files)
    if response.status_code == 200:
        print("Successfully got response:")
        print(response.json())
        return True
    else:
        print("Error:", response.status_code)
        print(response.text)
        return False


async def main():
    # load all files in test_files/
    import os

    test_files = os.listdir("test_files")
    files = [f"test_files/{file}" for file in test_files]

    PARALLEL = True

    if PARALLEL:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Kick off 5 tasks in parallel
            tasks = [test_extract_middle_json(client, path) for path in files]
            # Gather them all
            results = await asyncio.gather(*tasks)
            print("All done:", results)
    else:
        # Run sequentially
        async with httpx.AsyncClient(timeout=60.0) as client:
            for path in files:
                await test_extract_middle_json(client, path)


if __name__ == "__main__":
    asyncio.run(main())
