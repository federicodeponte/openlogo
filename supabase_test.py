#!/usr/bin/env python3
"""
Supabase Integration Test Script for Logo Storage
This script demonstrates how to set up and test the Supabase integration.
"""

import asyncio
import os
from supabase import create_client, Client
from fede_crawl4ai.logo_crawler import LogoCrawler

# Configuration - Replace with your actual Supabase credentials
SUPABASE_URL = "https://your-project.supabase.co"  # Replace with your project URL
SUPABASE_KEY = "your-supabase-anon-key"  # Replace with your anon key
OPENAI_API_KEY = "your-openai-api-key"  # Replace with your OpenAI API key

async def test_supabase_connection():
    """Test the Supabase connection and storage bucket."""
    try:
        # Initialize Supabase client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase client initialized successfully")
        
        # Test storage bucket access
        bucket_name = "logo-images"
        try:
            # List files in the bucket (should be empty initially)
            files = supabase.storage.from_(bucket_name).list()
            print(f"✅ Storage bucket '{bucket_name}' accessible")
            print(f"   Files in bucket: {len(files)}")
        except Exception as e:
            print(f"❌ Storage bucket '{bucket_name}' not accessible: {e}")
            print("   Make sure you've run the SQL setup script first!")
            return False
        
        # Test database connection
        try:
            # Query the logo_statistics view
            response = supabase.table('logo_statistics').select('*').execute()
            print("✅ Database connection successful")
            print(f"   Logo statistics: {response.data}")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            print("   Make sure you've run the SQL setup script first!")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False

async def test_logo_crawler_with_supabase():
    """Test the logo crawler with Supabase integration."""
    try:
        # Initialize the logo crawler with Supabase credentials
        crawler = LogoCrawler(
            api_key=OPENAI_API_KEY,
            use_azure=False,  # Set to True if using Azure OpenAI
            supabase_url=SUPABASE_URL,
            supabase_key=SUPABASE_KEY
        )
        
        print("✅ LogoCrawler initialized with Supabase integration")
        
        # Test with a simple website
        test_url = "https://simpl.de"
        print(f"\n🔍 Testing logo detection for: {test_url}")
        
        results = await crawler.crawl_website(test_url)
        
        if results:
            print(f"✅ Found {len(results)} logos")
            
            # Check which ones would be saved (company logos with confidence > 0.8)
            company_logos = []
            for result in results:
                if result.confidence > 0.8 and crawler.is_company_logo(result.description, result.url):
                    company_logos.append(result)
            
            print(f"📊 Company logos to be saved: {len(company_logos)}")
            
            for i, result in enumerate(company_logos):
                print(f"\nLogo {i+1}:")
                print(f"  URL: {result.url}")
                print(f"  Confidence: {result.confidence}")
                print(f"  Description: {result.description[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Logo crawler test failed: {e}")
        return False

async def test_database_queries():
    """Test the database queries and functions."""
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        print("\n📊 Testing database queries...")
        
        # Test logo statistics
        response = supabase.table('logo_statistics').select('*').execute()
        print(f"✅ Logo statistics: {response.data}")
        
        # Test high confidence logos function
        response = supabase.rpc('get_high_confidence_logos', {'min_confidence': 0.8}).execute()
        print(f"✅ High confidence logos: {len(response.data)} found")
        
        # Test company search function
        response = supabase.rpc('get_logos_by_company', {'company_name_param': 'Microsoft'}).execute()
        print(f"✅ Microsoft logos: {len(response.data)} found")
        
        return True
        
    except Exception as e:
        print(f"❌ Database query test failed: {e}")
        return False

def print_setup_instructions():
    """Print setup instructions."""
    print("""
🚀 Supabase Setup Instructions:

1. Create a Supabase account at https://supabase.com/
2. Create a new project
3. Go to SQL Editor in your Supabase dashboard
4. Copy and paste the contents of 'supabase_setup.sql'
5. Run the SQL script
6. Go to Settings > API to get your project URL and anon key
7. Update the configuration variables in this script:
   - SUPABASE_URL
   - SUPABASE_KEY
   - OPENAI_API_KEY

The SQL script will create:
✅ Storage bucket for logo images
✅ Database table for logo metadata
✅ Indexes for performance
✅ Helper functions and views
✅ Row Level Security policies
✅ Sample data for testing

After setup, you can use the logo crawler with cloud storage:
```python
crawler = LogoCrawler(
    api_key="your-openai-api-key",
    supabase_url="https://your-project.supabase.co",
    supabase_key="your-supabase-anon-key"
)
```
""")

async def main():
    """Main test function."""
    print("🔧 Supabase Integration Test")
    print("=" * 50)
    
    # Check if credentials are configured
    if SUPABASE_URL == "https://your-project.supabase.co" or SUPABASE_KEY == "your-supabase-anon-key":
        print_setup_instructions()
        return
    
    print("1. Testing Supabase connection...")
    if not await test_supabase_connection():
        print_setup_instructions()
        return
    
    print("\n2. Testing logo crawler with Supabase...")
    if not await test_logo_crawler_with_supabase():
        return
    
    print("\n3. Testing database queries...")
    if not await test_database_queries():
        return
    
    print("\n🎉 All tests passed! Supabase integration is working correctly.")

if __name__ == "__main__":
    asyncio.run(main()) 