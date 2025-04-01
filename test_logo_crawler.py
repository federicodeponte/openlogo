import asyncio
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from fede_crawl4ai import LogoCrawler

print("Script started")  # Debug output

# Add the current directory to the Python path
current_dir = Path(__file__).parent.absolute()
print(f"Current directory: {current_dir}")
print(f"Current working directory: {os.getcwd()}")
sys.path.append(str(current_dir))

print("Importing LogoCrawler...")  # Debug output

async def main():
    print("Main function started")  # Debug output
    print(f"Current directory: {os.getcwd()}")
    
    print("Importing LogoCrawler...")
    crawler = LogoCrawler()
    print("LogoCrawler instance created")
    
    # Crawl website and get ranked results
    results = await crawler.crawl_website("https://www.elenra.de")
    
    # Save results to JSON
    output_data = [
        {
            "url": result.url,
            "confidence": result.confidence,
            "description": result.description,
            "page_url": result.page_url,
            "image_hash": result.image_hash,
            "timestamp": result.timestamp.isoformat(),
            "is_header": result.is_header,
            "rank_score": result.rank_score
        }
        for result in results
    ]
    
    # Save to file
    output_file = "results.json"
    print(f"\nPreparing to save results...")
    print(f"JSON data length: {len(json.dumps(output_data))} bytes")
    print(f"Writing to file: {os.path.abspath(output_file)}")
    
    # Ensure directory exists and is writable
    directory = os.path.dirname(os.path.abspath(output_file))
    print(f"Directory exists: {os.path.exists(directory)}")
    print(f"Directory is writable: {os.access(directory, os.W_OK)}")
    
    # Write the file
    print("File opened for writing")
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    print("Data written")
    
    # Verify file was written
    print("File flushed")
    os.fsync(f.fileno())
    print("File synced")
    print("Results saved successfully")
    
    # Verify file exists and size
    print(f"File exists: {os.path.exists(output_file)}")
    print(f"File size: {os.path.getsize(output_file)} bytes")
    with open(output_file, 'r') as f:
        content = f.read()
        print(f"File content length: {len(content)} bytes")
    
    print("Script completed")

if __name__ == "__main__":
    print("Starting main...")  # Debug output
    asyncio.run(main())
    print("Script completed")  # Debug output 