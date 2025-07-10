-- Supabase Setup for Logo Storage Project
-- Run this SQL in your Supabase SQL Editor

-- 1. Create the storage bucket for logo images
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'logo-images',
  'logo-images',
  true,
  52428800, -- 50MB file size limit
  ARRAY['image/png', 'image/jpeg', 'image/jpg', 'image/webp']
);

-- 2. Create a table to track uploaded logo images
CREATE TABLE IF NOT EXISTS logo_images (
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

-- 3. Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_logo_images_filename ON logo_images(filename);
CREATE INDEX IF NOT EXISTS idx_logo_images_company_name ON logo_images(company_name);
CREATE INDEX IF NOT EXISTS idx_logo_images_website_url ON logo_images(website_url);
CREATE INDEX IF NOT EXISTS idx_logo_images_confidence_score ON logo_images(confidence_score);
CREATE INDEX IF NOT EXISTS idx_logo_images_created_at ON logo_images(created_at);

-- 4. Create a function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

-- 5. Create a trigger to automatically update the updated_at column
CREATE TRIGGER update_logo_images_updated_at
  BEFORE UPDATE ON logo_images
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- 6. Create a view for easy querying of logo statistics
CREATE OR REPLACE VIEW logo_statistics AS
SELECT 
  COUNT(*) as total_logos,
  COUNT(DISTINCT company_name) as unique_companies,
  COUNT(DISTINCT website_url) as unique_websites,
  AVG(confidence_score) as avg_confidence,
  MAX(created_at) as latest_upload,
  MIN(created_at) as first_upload
FROM logo_images;

-- 7. Create a function to get logos by company
CREATE OR REPLACE FUNCTION get_logos_by_company(company_name_param TEXT)
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
  FROM logo_images li
  WHERE li.company_name ILIKE '%' || company_name_param || '%'
  ORDER BY li.confidence_score DESC, li.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- 8. Create a function to get high-confidence logos
CREATE OR REPLACE FUNCTION get_high_confidence_logos(min_confidence DECIMAL(3,2) DEFAULT 0.8)
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
  FROM logo_images li
  WHERE li.confidence_score >= min_confidence
  ORDER BY li.confidence_score DESC, li.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- 9. Set up Row Level Security (RLS) policies
ALTER TABLE logo_images ENABLE ROW LEVEL SECURITY;

-- Allow public read access to logo images
CREATE POLICY "Allow public read access to logo images" ON logo_images
  FOR SELECT USING (true);

-- Allow authenticated users to insert logo images
CREATE POLICY "Allow authenticated users to insert logo images" ON logo_images
  FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- Allow users to update their own logo images (if you add user_id column later)
-- CREATE POLICY "Allow users to update their own logo images" ON logo_images
--   FOR UPDATE USING (auth.uid() = user_id);

-- 10. Create a function to clean up old logo images (optional)
CREATE OR REPLACE FUNCTION cleanup_old_logo_images(days_old INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
  deleted_count INTEGER;
BEGIN
  DELETE FROM logo_images 
  WHERE created_at < NOW() - INTERVAL '1 day' * days_old;
  
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- 11. Grant necessary permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON logo_images TO anon, authenticated;
GRANT ALL ON logo_statistics TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_logos_by_company(TEXT) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_high_confidence_logos(DECIMAL) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION cleanup_old_logo_images(INTEGER) TO authenticated;

-- 12. Create a sample query to test the setup
-- Uncomment and run this to test:
/*
INSERT INTO logo_images (
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

-- Test the functions
SELECT * FROM logo_statistics;
SELECT * FROM get_logos_by_company('Example');
SELECT * FROM get_high_confidence_logos(0.9);
*/ 