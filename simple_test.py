#!/usr/bin/env python3
"""
Simple test script for MinerU FastAPI endpoint
Tests the /file_parse endpoint with files from test_files directory
"""

import requests
import asyncio
import httpx
from pathlib import Path
import json
import time
import os
from mineru_types import MinerUResult

# API Key for Bearer authentication
API_KEY = os.getenv("API_KEY", "mamaistdiebeste")


def extract_mineru_result(content: dict) -> MinerUResult:
    """Extract and parse MinerU result from API response content.
    
    Args:
        content: Dictionary containing the API response data
        
    Returns:
        MinerUResult: Parsed Pydantic model
    """
    md_content = content.get('md_content', None)
    content_list = content.get('content_list', None)
    if content_list:
        content_list = json.loads(content_list)
    images = content.get('images', None)
    middle_json = content.get('middle_json', None)
    if middle_json:
        middle_json = json.loads(middle_json)
    
    return MinerUResult(
        middle_json=middle_json,
        content_list=content_list,
        md_content=md_content,
        images=images
    )


def test_file_parse_endpoint():
    """Test the /file_parse endpoint with files from test_files directory"""
    
    # API configuration
    api_url = "http://127.0.0.1:8000/file_parse"
    test_files_dir = Path(__file__).parent / "test_files"
    
    # Find all PDF and image files in test_files
    test_files = list(test_files_dir.glob("*.pdf")) + \
                 list(test_files_dir.glob("*.jpeg")) + \
                 list(test_files_dir.glob("*.jpg")) + \
                 list(test_files_dir.glob("*.png"))
    
    if not test_files:
        print(f"❌ No test files found in {test_files_dir}")
        return
    
    print(f"Found {len(test_files)} test files:")
    for f in test_files:
        print(f"  - {f.name}")
    
    # Test with first file
    test_file = test_files[0]
    print(f"\n🧪 Testing with file: {test_file.name}")
    
    # Prepare the request
    files = [("files", (test_file.name, open(test_file, "rb"), "application/pdf"))]
    
    data = {
        # "output_dir": "./output",
        "lang_list": ["latin", "en"],
        "backend": "hybrid-auto-engine", # "pipeline",
        "parse_method": "auto",
        "formula_enable": False,
        "table_enable": True,
        "return_md": True,
        "return_middle_json": True,
        "return_model_output": True,
        "return_content_list": True,
        "return_images": True,
        "response_format_zip": False,
    }
    
    try:
        print(f"📤 Sending request to {api_url}...")
        headers = {"Authorization": f"Bearer {API_KEY}"}
        response = requests.post(api_url, files=files, data=data, headers=headers, timeout=300)
        
        # Close the file
        files[0][1][1].close()
        
        if response.status_code == 200:
            print("✅ Request successful!")
            result = response.json()
            print(f"\nResponse summary:")
            print(f"  Backend: {result.get('backend')}")
            print(f"  Version: {result.get('version')}")
            print(f"  Results: {len(result.get('results', {}))} file(s)")
            
            # Show markdown content preview if available
            for filename, content in result.get('results', {}).items():
                print(f"KEYS for {filename}: {list(content.keys())}")
                mineru_result = extract_mineru_result(content)
                
                if 'md_content' in content and content['md_content']:
                    md_preview = content['md_content'][:200]
                    print(f"\n📄 Markdown preview for {filename}:")
                    print(f"  {md_preview}...")
                
                print(f"\n🧩 Parsed MinerUResult for {filename}")

                # Save MinerUResult as JSON
                output_response_dir = Path(f"output_path/{test_file.stem}")
                output_response_dir.mkdir(parents=True, exist_ok=True)
                mineru_result_file = output_response_dir / "mineru_result.json"
                with open(mineru_result_file, "w", encoding="utf-8") as f:
                    json.dump(mineru_result.model_dump(), f, indent=2, ensure_ascii=False)
                print(f"💾 MinerUResult saved to: {mineru_result_file}")

            
            # Save full response to file in output_path/<filename>/
            output_response_dir = Path(f"output_path/{test_file.stem}")
            output_response_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_response_dir / "test_response.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Full response saved to: {output_file}")
            
        else:
            print(f"❌ Request failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - is the API server running?")
        print("   Start it with: mineru-api --host 127.0.0.1 --port 8000")
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def test_multiple_files():
    """Test with multiple files at once"""
    
    api_url = "http://127.0.0.1:8000/file_parse"
    test_files_dir = Path(__file__).parent / "test_files"
    
    # Get first 2 PDF files
    test_files = list(test_files_dir.glob("*.pdf"))[:2]
    
    if len(test_files) < 2:
        print("⚠️ Not enough files for multi-file test")
        return
    
    print(f"\n🧪 Testing with multiple files:")
    for f in test_files:
        print(f"  - {f.name}")
    
    files = [("files", (f.name, open(f, "rb"), "application/pdf")) for f in test_files]
    
    data = {
        # "output_dir": "./output",
        "lang_list": ["latin", "en"],
        "backend": "hybrid-auto-engine", # "pipeline",
        "parse_method": "auto",
        "formula_enable": False,
        "table_enable": True,
        "return_md": True,
        "return_middle_json": True,
        "return_model_output": True,
        "return_content_list": True,
        "return_images": True,
        "response_format_zip": False,
    }
    
    try:
        print(f"📤 Sending multi-file request...")
        headers = {"Authorization": f"Bearer {API_KEY}"}
        response = requests.post(api_url, files=files, data=data, headers=headers, timeout=600)
        
        # Close all files
        for f in files:
            f[1][1].close()
        
        if response.status_code == 200:
            print("✅ Multi-file request successful!")
            result = response.json()
            print(f"  Processed {len(result.get('results', {}))} file(s)")
            
            # Parse and save results for each file
            for filename, content in result.get('results', {}).items():
                print(f"\nKEYS for {filename}: {list(content.keys())}")
                mineru_result = extract_mineru_result(content)
                
                if 'md_content' in content and content['md_content']:
                    md_preview = content['md_content'][:200]
                    print(f"📄 Markdown preview for {filename}:")
                    print(f"  {md_preview}...")
                
                print(f"🧩 Parsed MinerUResult for {filename}")

                # Save MinerUResult as JSON
                output_response_dir = Path(f"output_path/{filename}")
                output_response_dir.mkdir(parents=True, exist_ok=True)
                mineru_result_file = output_response_dir / "mineru_result.json"
                with open(mineru_result_file, "w", encoding="utf-8") as f:
                    json.dump(mineru_result.model_dump(), f, indent=2, ensure_ascii=False)
                print(f"💾 MinerUResult saved to: {mineru_result_file}")
                
                # Save full response
                full_response_file = output_response_dir / "test_response.json"
                with open(full_response_file, "w", encoding="utf-8") as f:
                    json.dump({filename: content}, f, indent=2, ensure_ascii=False)
                print(f"💾 Full response saved to: {full_response_file}")
                
        else:
            print(f"❌ Request failed with status code: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def send_single_file_async(client: httpx.AsyncClient, api_url: str, file_path: Path, file_index: int):
    """Send a single file asynchronously"""
    print(f"🚀 [{file_index}] Starting request for: {file_path.name}")
    start_time = time.time()
    
    try:
        with open(file_path, "rb") as f:
            files = {"files": (file_path.name, f, "application/pdf")}
            
            data = {
                "lang_list": ["latin", "en"],
                "backend": "hybrid-auto-engine",
                "parse_method": "auto",
                "formula_enable": False,
                "table_enable": True,
                "return_md": True,
                "return_middle_json": True,
                "return_model_output": True,
                "return_content_list": True,
                "return_images": True,
                "response_format_zip": False,
            }
            
            headers = {"Authorization": f"Bearer {API_KEY}"}
            response = await client.post(api_url, files=files, data=data, headers=headers, timeout=300.0)
        
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            print(f"✅ [{file_index}] Completed in {elapsed_time:.2f}s: {file_path.name}")
            result = response.json()
            
            # Process and save results
            for filename, content in result.get('results', {}).items():
                mineru_result = extract_mineru_result(content)
                
                # Save MinerUResult as JSON
                output_response_dir = Path(f"output_path/{file_path.stem}")
                output_response_dir.mkdir(parents=True, exist_ok=True)
                mineru_result_file = output_response_dir / "mineru_result.json"
                with open(mineru_result_file, "w", encoding="utf-8") as f:
                    json.dump(mineru_result.model_dump(), f, indent=2, ensure_ascii=False)
                
                # Save full response
                full_response_file = output_response_dir / "test_response.json"
                with open(full_response_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
                print(f"💾 [{file_index}] Saved results to: {output_response_dir}")
            
            return {"success": True, "file": file_path.name, "time": elapsed_time}
        else:
            print(f"❌ [{file_index}] Failed ({response.status_code}): {file_path.name}")
            return {"success": False, "file": file_path.name, "status": response.status_code, "time": elapsed_time}
            
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"❌ [{file_index}] Error after {elapsed_time:.2f}s: {file_path.name} - {str(e)}")
        return {"success": False, "file": file_path.name, "error": str(e), "time": elapsed_time}


async def test_parallel_single_files():
    """Test sending multiple single files in parallel using asyncio"""
    
    api_url = "http://127.0.0.1:8000/file_parse"
    test_files_dir = Path(__file__).parent / "test_files"
    
    # Get all test files
    test_files = list(test_files_dir.glob("*.pdf")) + \
                 list(test_files_dir.glob("*.jpeg")) + \
                 list(test_files_dir.glob("*.jpg")) + \
                 list(test_files_dir.glob("*.png"))
    
    if not test_files:
        print(f"❌ No test files found in {test_files_dir}")
        return
    
    # Limit to first 3 files for testing
    test_files = test_files[:3]
    
    print(f"\n🧪 Testing parallel requests with {len(test_files)} files:")
    for i, f in enumerate(test_files, 1):
        print(f"  [{i}] {f.name}")
    
    start_time = time.time()
    
    async with httpx.AsyncClient() as client:
        # Create tasks for each file
        tasks = [
            send_single_file_async(client, api_url, file_path, i)
            for i, file_path in enumerate(test_files, 1)
        ]
        
        # Run all tasks in parallel
        results = await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Parallel Test Summary:")
    print(f"{'='*60}")
    print(f"Total files: {len(test_files)}")
    print(f"Total time: {total_time:.2f}s")
    successful = sum(1 for r in results if r.get('success'))
    print(f"Successful: {successful}/{len(test_files)}")
    
    print(f"\nIndividual times:")
    for result in results:
        status = "✅" if result.get('success') else "❌"
        print(f"  {status} {result['file']}: {result['time']:.2f}s")


def test_warmup():
    """Warmup test to check API key and process demo files"""
    
    port = os.getenv("MINERU_API_PORT", "8000")
    api_url = f"http://127.0.0.1:{port}/file_parse"
    demo_dir = Path(__file__).parent / "demo" / "pdfs"
    
    # Check API key
    print("\n🔑 Checking API Key...")
    if not API_KEY:
        print("❌ No API_KEY configured!")
        return False
    print(f"✅ API Key configured: {API_KEY[:10]}...")
    
    # Check if demo files exist
    demo_files = list(demo_dir.glob("*.pdf"))
    if not demo_files:
        print(f"❌ No demo files found in {demo_dir}")
        return False
    
    print(f"\n📁 Found {len(demo_files)} demo files:")
    for f in demo_files:
        print(f"  - {f.name}")
    
    # Test with first demo file for warmup
    test_file = demo_files[0]
    print(f"\n🔥 Warming up with: {test_file.name}")
    
    files = [("files", (test_file.name, open(test_file, "rb"), "application/pdf"))]
    
    data = {
        "lang_list": ["latin", "en"],
        "backend": "hybrid-auto-engine",
        "parse_method": "auto",
        "formula_enable": False,
        "table_enable": True,
        "return_md": True,
        "return_middle_json": True,
        "return_model_output": True,
        "return_content_list": True,
        "return_images": True,
        "response_format_zip": False,
    }
    
    try:
        start_time = time.time()
        headers = {"Authorization": f"Bearer {API_KEY}"}
        response = requests.post(api_url, files=files, data=data, headers=headers, timeout=300)
        
        files[0][1][1].close()
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            print(f"✅ Warmup successful! ({elapsed:.2f}s)")
            result = response.json()
            
            for filename, content in result.get('results', {}).items():
                # Parse and validate with Pydantic model
                try:
                    mineru_result = extract_mineru_result(content)
                    print("✅ Pydantic validation passed")
                except Exception as e:
                    print(f"❌ Pydantic validation failed: {str(e)}")
                    return False
                
                md_content = content.get('md_content')
                if md_content:
                    preview = md_content[:150].replace('\n', ' ')
                    print(f"📄 Preview: {preview}...")
            
            return True
        else:
            print(f"❌ Warmup failed: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - is the API server running?")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("MinerU API Endpoint Test")
    print("=" * 60)
    
    # Run warmup test first
    print("\n" + "=" * 60)
    print("Warmup Test")
    print("=" * 60)
    warmup_success = test_warmup()
    
    if not warmup_success:
        print("\n⚠️ Warmup failed, skipping other tests")
        exit(1)
    
    # Test single file
    # test_file_parse_endpoint()
    
    # Test multiple files in one request
    # test_multiple_files()
    
    # Test parallel single file requests
    # print("\n" + "=" * 60)
    # print("Testing Parallel Single File Requests")
    # print("=" * 60)
    # asyncio.run(test_parallel_single_files())
    # 
    # print("\n" + "=" * 60)
    # print("Test completed")
    # print("=" * 60)
