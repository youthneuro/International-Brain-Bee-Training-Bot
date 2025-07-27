#!/usr/bin/env python3
"""
Migration script to move data from Supabase database tables to Supabase Storage files.
This script will help you transition from the old table-based storage to the new file-based storage.
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
import json
from datetime import datetime
from typing import Dict, List, Any

# Load environment variables
load_dotenv()

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Supabase credentials not found. Please set SUPABASE_URL and SUPABASE_ANON_KEY in your .env file")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def migrate_sessions():
    """Migrate session data from user_sessions table to storage files."""
    try:
        print("🔄 Migrating session data...")
        
        # Get all session data from the table
        result = supabase.table("user_sessions").select("*").execute()
        
        if not result.data:
            print("✅ No session data to migrate")
            return
        
        migrated_count = 0
        for session_record in result.data:
            try:
                session_data = session_record.get('session_data', {})
                session_id = session_data.get('session_id')
                
                if not session_id:
                    # Generate a session ID if none exists
                    import uuid
                    session_id = str(uuid.uuid4())
                    session_data['session_id'] = session_id
                
                # Create filename
                filename = f"sessions/{session_id}.json"
                
                # Convert to JSON
                json_data = json.dumps(session_data, separators=(',', ':'))
                
                # Upload to storage
                supabase.storage.from_("brain-bee-data").upload(
                    path=filename,
                    file=json_data.encode('utf-8'),
                    file_options={"content-type": "application/json"}
                )
                
                migrated_count += 1
                print(f"  ✅ Migrated session {session_id}")
                
            except Exception as e:
                print(f"  ❌ Failed to migrate session {session_record.get('id')}: {e}")
                continue
        
        print(f"✅ Successfully migrated {migrated_count} sessions")
        
    except Exception as e:
        print(f"❌ Error migrating sessions: {e}")

def migrate_feedback():
    """Migrate feedback data from feedback_scores table to storage files."""
    try:
        print("🔄 Migrating feedback data...")
        
        # Get all feedback data from the table
        result = supabase.table("feedback_scores").select("*").execute()
        
        if not result.data:
            print("✅ No feedback data to migrate")
            return
        
        migrated_count = 0
        for feedback_record in result.data:
            try:
                # Create timestamp
                created_at = feedback_record.get('created_at', datetime.now().isoformat())
                if isinstance(created_at, str):
                    timestamp = created_at
                else:
                    timestamp = created_at.isoformat()
                
                # Generate unique filename
                import uuid
                feedback_id = str(uuid.uuid4())
                filename = f"feedback/{timestamp}_{feedback_id}.json"
                
                # Create feedback JSON
                feedback_data = {
                    "question": feedback_record.get('question', ''),
                    "user_answer": feedback_record.get('user_answer', ''),
                    "correct_answer": feedback_record.get('correct_answer', ''),
                    "evaluation": feedback_record.get('evaluation', ''),
                    "category": feedback_record.get('category', ''),
                    "is_correct": feedback_record.get('is_correct', False),
                    "timestamp": timestamp,
                    "feedback_id": feedback_id
                }
                
                # Convert to JSON
                json_data = json.dumps(feedback_data, separators=(',', ':'))
                
                # Upload to storage
                supabase.storage.from_("brain-bee-data").upload(
                    path=filename,
                    file=json_data.encode('utf-8'),
                    file_options={"content-type": "application/json"}
                )
                
                migrated_count += 1
                print(f"  ✅ Migrated feedback {feedback_id}")
                
            except Exception as e:
                print(f"  ❌ Failed to migrate feedback {feedback_record.get('id')}: {e}")
                continue
        
        print(f"✅ Successfully migrated {migrated_count} feedback entries")
        
    except Exception as e:
        print(f"❌ Error migrating feedback: {e}")

def verify_migration():
    """Verify that the migration was successful."""
    try:
        print("🔍 Verifying migration...")
        
        # Check session files
        session_files = supabase.storage.from_("brain-bee-data").list("sessions")
        session_count = len(session_files) if session_files else 0
        
        # Check feedback files
        feedback_files = supabase.storage.from_("brain-bee-data").list("feedback")
        feedback_count = len(feedback_files) if feedback_files else 0
        
        print(f"📁 Found {session_count} session files")
        print(f"📁 Found {feedback_count} feedback files")
        
        # Check if tables still exist and have data
        try:
            session_result = supabase.table("user_sessions").select("id").execute()
            table_session_count = len(session_result.data) if session_result.data else 0
            
            feedback_result = supabase.table("feedback_scores").select("id").execute()
            table_feedback_count = len(feedback_result.data) if feedback_result.data else 0
            
            print(f"📊 Original table data: {table_session_count} sessions, {table_feedback_count} feedback entries")
            
            if session_count > 0 and feedback_count > 0:
                print("✅ Migration appears successful!")
                print("💡 You can now safely delete the old tables if desired.")
            else:
                print("⚠️  Migration may be incomplete. Please check the data.")
                
        except Exception as e:
            print(f"⚠️  Could not verify table data: {e}")
        
    except Exception as e:
        print(f"❌ Error verifying migration: {e}")

def cleanup_old_tables():
    """Remove the old tables after successful migration."""
    try:
        print("🗑️  Cleaning up old tables...")
        
        # Drop the old tables
        supabase.table("feedback_scores").delete().neq("id", 0).execute()
        supabase.table("user_sessions").delete().neq("id", 0).execute()
        
        print("✅ Old tables cleaned up")
        print("💡 You can now drop the tables entirely if desired:")
        print("   DROP TABLE IF EXISTS user_sessions;")
        print("   DROP TABLE IF EXISTS feedback_scores;")
        print("   DROP VIEW IF EXISTS feedback_analytics;")
        
    except Exception as e:
        print(f"❌ Error cleaning up tables: {e}")

def main():
    """Main migration function."""
    print("🚀 Brain Bee Training Bot - Migration to File Storage")
    print("=" * 60)
    
    # Check if storage bucket exists
    try:
        buckets = supabase.storage.list_buckets()
        bucket_names = [bucket['name'] for bucket in buckets]
        
        if 'brain-bee-data' not in bucket_names:
            print("❌ Storage bucket 'brain-bee-data' not found!")
            print("📋 Please create the bucket first:")
            print("   1. Go to your Supabase Dashboard")
            print("   2. Navigate to Storage")
            print("   3. Click 'Create a new bucket'")
            print("   4. Name it 'brain-bee-data'")
            print("   5. Set it to public")
            print("   6. Run the SQL from supabase_storage_setup.sql")
            return
        else:
            print("✅ Storage bucket 'brain-bee-data' found")
            
    except Exception as e:
        print(f"❌ Error checking storage bucket: {e}")
        return
    
    # Run migration
    print("\n🔄 Starting migration...")
    
    # Migrate sessions
    migrate_sessions()
    
    # Migrate feedback
    migrate_feedback()
    
    # Verify migration
    print("\n🔍 Verifying migration...")
    verify_migration()
    
    # Ask about cleanup
    print("\n" + "=" * 60)
    response = input("🗑️  Do you want to clean up the old tables? (y/N): ").lower().strip()
    
    if response in ['y', 'yes']:
        cleanup_old_tables()
    else:
        print("💡 Tables left intact. You can clean them up later.")
    
    print("\n✅ Migration completed!")
    print("🎉 Your app is now using file-based storage!")

if __name__ == "__main__":
    main() 