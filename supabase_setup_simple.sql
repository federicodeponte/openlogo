-- Supabase Setup for Logo Storage Project (Step-by-Step)
-- Run each section separately in your Supabase SQL Editor

-- STEP 1: Create the main table for logo images
CREATE TABLE IF NOT EXISTS public.logo_images (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  filename TEXT NOT NULL,
  original_url TEXT NOT NULL,
  background_removed_url TEXT,
  cloud_storage_url TEXT,
  company_name TEXT,
  website_url TEXT,
  confidence_score DECIMAL(3,2),
  description TEXT,
  image_hash TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- STEP 2: Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_logo_images_filename ON public.logo_images(filename);
CREATE INDEX IF NOT EXISTS idx_logo_images_company_name ON public.logo_images(company_name);
CREATE INDEX IF NOT EXISTS idx_logo_images_website_url ON public.logo_images(website_url);
CREATE INDEX IF NOT EXISTS idx_logo_images_confidence_score ON public.logo_images(confidence_score);
CREATE INDEX IF NOT EXISTS idx_logo_images_created_at ON public.logo_images(created_at);

-- STEP 3: Create a function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

-- STEP 4: Create a trigger to automatically update the updated_at column
CREATE TRIGGER update_logo_images_updated_at
  BEFORE UPDATE ON public.logo_images
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- STEP 5: Create a view for logo statistics
CREATE OR REPLACE VIEW public.logo_statistics AS
SELECT 
  COUNT(*) as total_logos,
  COUNT(DISTINCT company_name) as unique_companies,
  COUNT(DISTINCT website_url) as unique_websites,
  AVG(confidence_score) as avg_confidence,
  MAX(created_at) as latest_upload,
  MIN(created_at) as first_upload
FROM public.logo_images;

-- STEP 6: Create function to get logos by company
CREATE OR REPLACE FUNCTION public.get_logos_by_company(company_name_param TEXT)
RETURNS TABLE (
  id UUID,
  filename TEXT,
  original_url TEXT,
  background_removed_url TEXT,
  cloud_storage_url TEXT,
  confidence_score DECIMAL(3,2),
  description TEXT,
  created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    li.id,
    li.filename,
    li.original_url,
    li.background_removed_url,
    li.cloud_storage_url,
    li.confidence_score,
    li.description,
    li.created_at
  FROM public.logo_images li
  WHERE li.company_name ILIKE '%' || company_name_param || '%'
  ORDER BY li.confidence_score DESC, li.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- STEP 7: Create function to get high-confidence logos
CREATE OR REPLACE FUNCTION public.get_high_confidence_logos(min_confidence DECIMAL(3,2) DEFAULT 0.8)
RETURNS TABLE (
  id UUID,
  filename TEXT,
  company_name TEXT,
  website_url TEXT,
  confidence_score DECIMAL(3,2),
  cloud_storage_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    li.id,
    li.filename,
    li.company_name,
    li.website_url,
    li.confidence_score,
    li.cloud_storage_url,
    li.created_at
  FROM public.logo_images li
  WHERE li.confidence_score >= min_confidence
  ORDER BY li.confidence_score DESC, li.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- STEP 8: Set up Row Level Security (RLS)
ALTER TABLE public.logo_images ENABLE ROW LEVEL SECURITY;

-- Allow public read access
CREATE POLICY "Allow public read access to logo images" ON public.logo_images
  FOR SELECT USING (true);

-- Allow authenticated users to insert
CREATE POLICY "Allow authenticated users to insert logo images" ON public.logo_images
  FOR INSERT WITH CHECK (true);

-- STEP 9: Grant permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON public.logo_images TO anon, authenticated;
GRANT SELECT ON public.logo_statistics TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_logos_by_company(TEXT) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_high_confidence_logos(DECIMAL) TO anon, authenticated;

-- STEP 10: Insert sample data for testing (optional)
INSERT INTO public.logo_images (
  filename, 
  original_url, 
  background_removed_url, 
  cloud_storage_url, 
  company_name, 
  website_url, 
  confidence_score, 
  description, 
  image_hash
) VALUES (
  'test_logo_1.png',
  'https://example.com/logo.png',
  'https://example.com/logo_no_bg.png',
  'https://your-project.supabase.co/storage/v1/object/public/logo-images/background-removed/test_logo_1.png',
  'Example Corp',
  'https://example.com',
  0.95,
  'This is a test logo description',
  'abc123def456'
);

-- Test queries
SELECT * FROM public.logo_statistics;
SELECT * FROM public.get_logos_by_company('Example');
SELECT * FROM public.get_high_confidence_logos(0.8); 