import asyncio
import os
import sys
import json
import ssl
import aiohttp
from pathlib import Path
from datetime import datetime
from fede_crawl4ai import LogoCrawler
import chardet

print("Script started")  # Debug output

# Add the current directory to the Python path
current_dir = Path(__file__).parent.absolute()
print(f"Current directory: {current_dir}")
print(f"Current working directory: {os.getcwd()}")
sys.path.append(str(current_dir))

# Configure SSL context to be more permissive
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Browser-like headers
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',  # Added German language preference
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1'
}

print("Importing LogoCrawler...")  # Debug output

async def test_connection(url: str) -> bool:
    """Test if we can connect to the website."""
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        conn = aiohttp.TCPConnector(ssl=ssl_context, force_close=True)
        async with aiohttp.ClientSession(headers=headers, timeout=timeout, connector=conn) as session:
            print(f"Attempting to connect to {url}...")
            async with session.get(url) as response:
                print(f"Connection test response status: {response.status}")
                if response.status == 200:
                    content = await response.read()
                    # Detect the encoding
                    encoding_result = chardet.detect(content)
                    print(f"Detected encoding: {encoding_result}")
                    
                    # Try different encodings
                    encodings = [
                        encoding_result['encoding'],
                        'iso-8859-1',
                        'windows-1252',
                        'utf-8',
                        'latin1'
                    ]
                    
                    for encoding in encodings:
                        if not encoding:
                            continue
                        try:
                            text = content.decode(encoding)
                            print(f"Successfully decoded content using {encoding} encoding")
                            print(f"Retrieved {len(text)} characters")
                            return True
                        except UnicodeDecodeError:
                            print(f"Failed to decode with {encoding}")
                            continue
                    
                    print("Failed to decode content with any encoding")
                    return False
                else:
                    print(f"Server responded with status {response.status}")
                    return False
    except Exception as e:
        print(f"Connection test error: {str(e)}")
        print(f"Error type: {type(e)}")
        return False

async def main():
    print("Script started")
    print(f"Current directory: {os.getcwd()}")
    
    # Try different variations of the URL
    urls = [
        "https://city-map.de",
        "http://city-map.de",
        "https://www.city-map.de",
        "http://www.city-map.de"
    ]
    
    connected = False
    working_url = None
    
    for url in urls:
        print(f"\nTesting connection to {url}...")
        if await test_connection(url):
            print(f"Successfully connected to {url}")
            connected = True
            working_url = url
            break
        else:
            print(f"Failed to connect to {url}")
    
    if not connected:
        print("\nWarning: Could not connect to any variation of the website.")
        print("The site might be blocking automated requests or be temporarily unavailable.")
        print("You might want to try:")
        print("1. Using a VPN")
        print("2. Checking if the website is accessible in your browser")
        print("3. Checking if the website requires specific cookies or authentication")
        return
    
    print("\nCreating LogoCrawler instance...")
    # You can add your Twitter API key here if you have one
    crawler = LogoCrawler(twitter_api_key=None)
    print("LogoCrawler instance created")
    
    # Crawl website and get ranked results
    print(f"\nStarting crawl of {working_url}...")
    try:
        results = await crawler.crawl_website(working_url)
    except Exception as e:
        print(f"Error during crawl: {str(e)}")
        return
    
    # Process and classify results
    processed_results = []
    for result in results:
        # Determine classification based on characteristics
        if result.is_header and "city-map" in result.description.lower():
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
    
    # Save to results_city_map.json
    print("Writing to file: results_city_map.json")
    try:
        with open("results_city_map.json", "w") as f:
            f.write(json_data)
        print("Results saved successfully to results_city_map.json")
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