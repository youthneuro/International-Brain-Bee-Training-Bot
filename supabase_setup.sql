-- Supabase setup for Brain Bee Training Bot
-- Run this in your Supabase SQL editor

-- Create user_sessions table for persistent session storage
CREATE TABLE IF NOT EXISTS user_sessions (
    id BIGSERIAL PRIMARY KEY,
    session_data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create feedback_scores table for storing question feedback
CREATE TABLE IF NOT EXISTS feedback_scores (
    id BIGSERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    user_answer TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    evaluation TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_sessions_updated_at ON user_sessions(updated_at);
CREATE INDEX IF NOT EXISTS idx_feedback_scores_created_at ON feedback_scores(created_at);

-- Enable Row Level Security (RLS) - optional, can be disabled if causing issues
-- ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE feedback_scores ENABLE ROW LEVEL SECURITY;

-- Create policies for RLS (optional)
-- CREATE POLICY "Users can view their own sessions" ON user_sessions
--     FOR SELECT USING (auth.uid()::text = user_id);

-- CREATE POLICY "Users can insert their own sessions" ON user_sessions
--     FOR INSERT WITH CHECK (auth.uid()::text = user_id);

-- CREATE POLICY "Users can update their own sessions" ON user_sessions
--     FOR UPDATE USING (auth.uid()::text = user_id);

-- CREATE POLICY "Users can view their own feedback" ON feedback_scores
--     FOR SELECT USING (auth.uid()::text = user_id);

-- CREATE POLICY "Users can insert their own feedback" ON feedback_scores
--     FOR INSERT WITH CHECK (auth.uid()::text = user_id);

-- Grant necessary permissions
GRANT ALL ON user_sessions TO anon, authenticated;
GRANT ALL ON feedback_scores TO anon, authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated; 