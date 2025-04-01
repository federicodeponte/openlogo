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
    print("Script started")
    print(f"Current directory: {os.getcwd()}")
    
    print("Creating LogoCrawler instance...")
    # You can add your Twitter API key here if you have one
    crawler = LogoCrawler(twitter_api_key=None)
    print("LogoCrawler instance created")
    
    # Crawl website and get ranked results
    print("\nStarting crawl of www.enter.de...")
    results = await crawler.crawl_website("https://www.enter.de")
    
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
            "rank_score": result.rank_score,
            "detection_scores": result.detection_scores
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
    
    # Print summary of results
    print("\nResults Summary:")
    print(f"Total logos found: {len(results)}")
    
    # Sort by rank score
    sorted_results = sorted(results, key=lambda x: x.rank_score, reverse=True)
    
    print("\nTop 3 most likely logos:")
    for i, result in enumerate(sorted_results[:3], 1):
        location = "header/navigation" if result.is_header else "main content"
        print(f"\n{i}. Logo from {location}")
        print(f"URL: {result.url}")
        print(f"Confidence: {result.confidence}")
        print(f"Rank Score: {result.rank_score}")
        print(f"Description: {result.description}")
        if result.detection_scores:
            print("\nDetection Scores:")
            for category, scores in result.detection_scores.items():
                avg_score = sum(scores.values()) / len(scores)
                print(f"- {category}: {avg_score:.2f}")
    
    print("\nScript completed")

if __name__ == "__main__":
    print("Starting main...")  # Debug output
    asyncio.run(main())
    print("Script completed")  # Debug output 