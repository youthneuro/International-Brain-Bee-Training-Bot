-- Supabase Storage Setup for Brain Bee Training Bot
-- This setup uses Supabase Storage for JSON file storage instead of database tables

-- Note: This file contains the SQL commands to set up storage buckets
-- The actual bucket creation is done through the Supabase Dashboard

-- ========================================
-- STORAGE BUCKET SETUP
-- ========================================

-- Create the main storage bucket for brain bee data
-- This should be done through the Supabase Dashboard:
-- 1. Go to Storage in your Supabase project
-- 2. Click "Create a new bucket"
-- 3. Name it "brain-bee-data"
-- 4. Set it to public (or private if you prefer)

-- ========================================
-- STORAGE POLICIES
-- ========================================

-- Allow public read access to brain-bee-data bucket
-- This allows the app to read session and feedback files
CREATE POLICY "Public read access to brain-bee-data" ON storage.objects
    FOR SELECT USING (bucket_id = 'brain-bee-data');

-- Allow public insert access to brain-bee-data bucket
-- This allows the app to create session and feedback files
CREATE POLICY "Public insert access to brain-bee-data" ON storage.objects
    FOR INSERT WITH CHECK (bucket_id = 'brain-bee-data');

-- Allow public update access to brain-bee-data bucket
-- This allows the app to update session files
CREATE POLICY "Public update access to brain-bee-data" ON storage.objects
    FOR UPDATE USING (bucket_id = 'brain-bee-data');

-- Allow public delete access to brain-bee-data bucket
-- This allows the app to cleanup old files
CREATE POLICY "Public delete access to brain-bee-data" ON storage.objects
    FOR DELETE USING (bucket_id = 'brain-bee-data');

-- ========================================
-- FILE STRUCTURE
-- ========================================

-- The storage bucket will contain the following structure:
-- brain-bee-data/
-- ├── sessions/
-- │   ├── {session_id}.json          -- User session data
-- │   └── ...
-- └── feedback/
--     ├── {timestamp}_{feedback_id}.json  -- Individual feedback entries
--     └── ...

-- ========================================
-- SESSION FILE FORMAT
-- ========================================

-- Each session file contains:
-- {
--   "session_id": "uuid",
--   "history": [
--     {
--       "question": "What is...",
--       "choices": ["A", "B", "C", "D"],
--       "user_answer": "A",
--       "correct_answer": "B",
--       "feedback": "Incorrect. The correct answer was B..."
--     }
--   ],
--   "current_question": {...},
--   "score": 5,
--   "total_questions": 10
-- }

-- ========================================
-- FEEDBACK FILE FORMAT
-- ========================================

-- Each feedback file contains:
-- {
--   "question": "What is...",
--   "user_answer": "A",
--   "correct_answer": "B",
--   "evaluation": "Detailed evaluation...",
--   "category": "Sensory system",
--   "is_correct": false,
--   "timestamp": "2024-01-15T10:30:00Z",
--   "feedback_id": "uuid"
-- }

-- ========================================
-- ADVANTAGES OF FILE-BASED STORAGE
-- ========================================

-- 1. SIMPLER STRUCTURE
--    - No complex database schema
--    - Easy to understand and maintain
--    - JSON files are human-readable

-- 2. FLEXIBLE DATA
--    - Can store any JSON structure
--    - Easy to add new fields
--    - No schema migrations needed

-- 3. BETTER PERFORMANCE
--    - Direct file access
--    - No complex queries
--    - Faster for large datasets

-- 4. EASIER BACKUP
--    - Files can be easily exported
--    - Simple to migrate between systems
--    - Version control friendly

-- 5. COST EFFECTIVE
--    - Supabase Storage is cheaper than database rows
--    - Better for large amounts of data
--    - More storage space available

-- ========================================
-- MIGRATION FROM TABLES TO FILES
-- ========================================

-- If you have existing data in tables, you can migrate it:

-- 1. Export existing session data:
-- SELECT session_data FROM user_sessions;

-- 2. Export existing feedback data:
-- SELECT * FROM feedback_scores;

-- 3. Convert to JSON files and upload to storage

-- ========================================
-- CLEANUP OLD TABLES (OPTIONAL)
-- ========================================

-- After migrating data and confirming everything works:
-- DROP TABLE IF EXISTS user_sessions;
-- DROP TABLE IF EXISTS feedback_scores;
-- DROP VIEW IF EXISTS feedback_analytics;

-- ========================================
-- MONITORING AND MAINTENANCE
-- ========================================

-- Check storage usage:
-- SELECT 
--   bucket_id,
--   COUNT(*) as file_count,
--   SUM(metadata->>'size')::bigint as total_size
-- FROM storage.objects 
-- WHERE bucket_id = 'brain-bee-data'
-- GROUP BY bucket_id;

-- List all files:
-- SELECT name, metadata FROM storage.objects 
-- WHERE bucket_id = 'brain-bee-data'
-- ORDER BY created_at DESC;

-- ========================================
-- SECURITY CONSIDERATIONS
-- ========================================

-- The current setup allows public access to the storage bucket
-- For production, you might want to:
-- 1. Make the bucket private
-- 2. Use Row Level Security (RLS)
-- 3. Implement user authentication
-- 4. Add rate limiting

-- Example RLS policy for authenticated users only:
-- CREATE POLICY "Authenticated users only" ON storage.objects
--     FOR ALL USING (auth.role() = 'authenticated'); 