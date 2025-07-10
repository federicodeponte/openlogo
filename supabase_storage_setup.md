# Supabase Storage Setup Instructions

## Step 1: Create Storage Bucket (Manual Setup in Dashboard)

1. **Go to Storage** in your Supabase dashboard
2. **Click "Create Bucket"**
3. **Use these settings:**
   - **Bucket name:** `logo-images`
   - **Public bucket:** ✅ **Enabled** (so images can be accessed via public URLs)
   - **File size limit:** `50MB`
   - **Allowed MIME types:** `image/png, image/jpeg, image/jpg, image/webp`

4. **Click "Create Bucket"**

## Step 2: Set Bucket Policies (Optional - for fine-grained control)

If you want to set custom policies for the storage bucket, go to **Storage > Policies** and add:

```sql
-- Allow public access to read files
CREATE POLICY "Public Access" ON storage.objects FOR SELECT USING (bucket_id = 'logo-images');

-- Allow authenticated users to upload files
CREATE POLICY "Authenticated Upload" ON storage.objects FOR INSERT WITH CHECK (bucket_id = 'logo-images' AND auth.role() = 'authenticated');
```

## Step 3: Test Storage Access

After creating the bucket, test it with this URL format:
```
https://your-project.supabase.co/storage/v1/object/public/logo-images/your-file.png
```

## Alternative: Programmatic Bucket Creation

If you prefer to create the bucket via code, you can use this JavaScript in the browser console:

```javascript
// Only works if you're logged in to Supabase dashboard
const { createClient } = supabase
const supabaseUrl = 'https://your-project.supabase.co'
const supabaseKey = 'your-service-role-key' // Use service role key, not anon key

const client = createClient(supabaseUrl, supabaseKey)

client.storage.createBucket('logo-images', {
  public: true,
  fileSizeLimit: 52428800, // 50MB
  allowedMimeTypes: ['image/png', 'image/jpeg', 'image/jpg', 'image/webp']
})
```

## Next Steps

After setting up the storage bucket:

1. Run the SQL setup script (`supabase_setup_simple.sql`) in the SQL Editor
2. Test the integration with `python3 supabase_test.py`
3. Use the logo crawler with Supabase credentials

## Troubleshooting

**If you get permission errors:**
- Make sure the bucket is set to "Public"
- Check that your Supabase project has the correct permissions
- Verify your API keys are correct (use anon key for client, service role for admin operations)

**If uploads fail:**
- Check file size limits
- Verify MIME types are allowed
- Ensure your Supabase project has enough storage quota 