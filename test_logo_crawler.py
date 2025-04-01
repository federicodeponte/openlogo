import asyncio
import os
import sys
import json
from pathlib import Path
from datetime import datetime

print("Script started")  # Debug output

# Add the current directory to the Python path
current_dir = Path(__file__).parent.absolute()
print(f"Current directory: {current_dir}")
print(f"Current working directory: {os.getcwd()}")
sys.path.append(str(current_dir))

print("Importing LogoCrawler...")  # Debug output
from fede_crawl4ai.logo_crawler import LogoCrawler
print("LogoCrawler imported successfully")  # Debug output

async def main():
    print("Main function started")  # Debug output
    # Set up the OpenAI API key
    api_key = "COIEsidMCl1pXiM33rWGJTNeF2fyheRJXc9FaYFqCEidCYwQPGaHJQQJ99BAACPV0roXJ3w3AAABACOGB3cH"
    
    # Create an instance of LogoCrawler
    print("Creating LogoCrawler instance...")  # Debug output
    crawler = LogoCrawler(api_key=api_key)
    print("LogoCrawler instance created")  # Debug output
    
    # URL to crawl
    url = "https://www.elenra.de"
    
    # Generate output filename based on domain
    domain = url.replace("https://", "").replace("http://", "").split("/")[0]
    output_file = os.path.join(os.getcwd(), "results.json")
    print(f"Will save results to: {output_file}")
    
    # Crawl for logos
    print("Starting logo crawl...")  # Debug output
    results = await crawler.crawl_for_logos(url, max_pages=10)
    print(f"Crawl completed. Found {len(results)} results")  # Debug output
    
    # Print results
    print("\nFound logos:")
    for result in results:
        print(f"\nURL: {result.url}")
        print(f"Confidence: {result.confidence}")
        print(f"Description: {result.description}")
        print(f"Page URL: {result.page_url}")
        print("-" * 50)
    
    # Save results to file
    try:
        print(f"\nPreparing to save results...")
        results_dict = []
        for result in results:
            result_dict = {
                "url": result.url,
                "confidence": result.confidence,
                "description": result.description,
                "page_url": result.page_url,
                "image_hash": result.image_hash,
                "timestamp": result.timestamp.isoformat()
            }
            results_dict.append(result_dict)
        
        # Convert to string first
        json_data = json.dumps(results_dict, indent=2)
        print(f"JSON data length: {len(json_data)} bytes")
        
        # Write to file
        print(f"Writing to file: {output_file}")
        print(f"Directory exists: {os.path.exists(os.path.dirname(output_file))}")
        print(f"Directory is writable: {os.access(os.path.dirname(output_file), os.W_OK)}")
        
        with open(output_file, 'w') as f:
            print("File opened for writing")
            f.write(json_data)
            print("Data written")
            f.flush()
            print("File flushed")
            os.fsync(f.fileno())
            print("File synced")
        print(f"Results saved successfully")
        
        # Verify file was written
        if os.path.exists(output_file):
            print(f"File exists: {output_file}")
            print(f"File size: {os.path.getsize(output_file)} bytes")
            
            # Read back the file to verify
            with open(output_file, 'r') as f:
                content = f.read()
                print(f"File content length: {len(content)} bytes")
        else:
            print(f"Warning: File does not exist: {output_file}")
    
    except Exception as e:
        print(f"Error saving results: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting main...")  # Debug output
    asyncio.run(main())
    print("Script completed")  # Debug output 