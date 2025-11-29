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
    print("\nStarting crawl of www.elenra.de...")
    results = await crawler.crawl_website("https://www.elenra.de")
    
    # Process and classify results
    processed_results = []
    for result in results:
        # Determine classification based on characteristics
        if result.is_header and "elenra" in result.description.lower():
            classification = "company"
        elif any(partner in result.description.lower() for partner in ["google", "facebook", "twitter", "linkedin"]):
            classification = "third_party"
        else:
            classification = "design_element"
        
        # Create new result with classification
        processed_result = {
            "url": result.url,
            "confidence": result.confidence,
            "description": result.description,
            "page_url": result.page_url,
            "image_hash": result.image_hash,
            "timestamp": result.timestamp.isoformat(),
            "is_header": result.is_header,
            "rank_score": result.rank_score,
            "detection_scores": result.detection_scores,
            "classification": classification,
            "location": "header/navigation" if result.is_header else "main content"
        }
        processed_results.append(processed_result)
    
    print("\nFound logos (ranked by likelihood of being main company logo):")
    print("\nCompany Logos:")
    print("-" * 50)
    for result in processed_results:
        if result["classification"] == "company":
            print(f"URL: {result['url']}")
            print(f"Location: {result['location']}")
            print(f"Confidence: {result['confidence']:.2f}")
            print(f"Rank Score: {result['rank_score']:.2f}")
            print(f"Description: {result['description']}")
            print(f"Page URL: {result['page_url']}")
            print("-" * 50)
    
    print("\nPartner/Third-party Logos:")
    print("-" * 50)
    for result in processed_results:
        if result["classification"] == "third_party":
            print(f"URL: {result['url']}")
            print(f"Location: {result['location']}")
            print(f"Confidence: {result['confidence']:.2f}")
            print(f"Rank Score: {result['rank_score']:.2f}")
            print(f"Description: {result['description']}")
            print(f"Page URL: {result['page_url']}")
            print("-" * 50)
    
    print("\nDesign Elements:")
    print("-" * 50)
    for result in processed_results:
        if result["classification"] == "design_element":
            print(f"URL: {result['url']}")
            print(f"Location: {result['location']}")
            print(f"Confidence: {result['confidence']:.2f}")
            print(f"Rank Score: {result['rank_score']:.2f}")
            print(f"Description: {result['description']}")
            print(f"Page URL: {result['page_url']}")
            print("-" * 50)
    
    print("\nResults Summary:")
    print(f"Total logos found: {len(processed_results)}")
    print(f"Company logos: {sum(1 for r in processed_results if r['classification'] == 'company')}")
    print(f"Partner/Third-party logos: {sum(1 for r in processed_results if r['classification'] == 'third_party')}")
    print(f"Design elements: {sum(1 for r in processed_results if r['classification'] == 'design_element')}")
    
    # Save results to JSON file
    print("\nPreparing to save results...")
    json_data = json.dumps(processed_results, indent=2)
    print(f"JSON data length: {len(json_data)} bytes")
    
    # Save to results.json
    print("Writing to file: results.json")
    try:
        with open("results.json", "w") as f:
            f.write(json_data)
        print("Results saved successfully to results.json")
    except Exception as e:
        print(f"Error saving results: {str(e)}")
    
    # Print summary of results
    print("\nResults Summary:")
    print(f"Total logos found: {len(processed_results)}")
    
    # Sort by rank score
    sorted_results = sorted(processed_results, key=lambda x: x['rank_score'], reverse=True)
    
    print("\nTop 3 most likely logos:")
    for i, result in enumerate(sorted_results[:3], 1):
        location = "header/navigation" if result['is_header'] else "main content"
        print(f"\n{i}. Logo from {location}")
        print(f"URL: {result['url']}")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Rank Score: {result['rank_score']:.2f}")
        print(f"Description: {result['description']}")
        if result['detection_scores']:
            print("\nDetection Scores:")
            for score in result['detection_scores']:
                print(f"- {score}")
    
    print("\nScript completed")

if __name__ == "__main__":
    print("Starting main...")  # Debug output
    asyncio.run(main())
    print("Script completed")  # Debug output 