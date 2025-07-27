#!/usr/bin/env python3
"""
Test script to verify ratings are being generated and stored correctly.
"""

import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

def test_rating_generation():
    """Test that ratings are being generated correctly."""
    print("🔍 Testing Rating Generation...")
    print("=" * 50)
    
    try:
        from openai import AzureOpenAI
        
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-02-15-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", "")
        )
        
        # Test question and evaluation
        test_question = "What is the primary function of the auditory cortex?"
        test_answer = "B"
        test_explanation = "The auditory cortex processes sound information and is responsible for hearing."
        
        eval_prompt = (
            f"You are evaluating a neuroscience multiple-choice quiz question. "
            f"Please provide your evaluation in the following EXACT JSON format:\n\n"
            f"{{\n"
            f"  \"question_quality_rating\": [1-10],\n"
            f"  \"answer_correctness_rating\": [1-10],\n"
            f"  \"question_quality_justification\": \"[Detailed explanation of question quality rating]\",\n"
            f"  \"answer_correctness_justification\": \"[Detailed explanation of answer correctness rating]\",\n"
            f"  \"overall_assessment\": \"[Overall assessment of the question and answer]\",\n"
            f"  \"difficulty_level\": \"[easy/medium/hard/expert]\",\n"
            f"  \"suggested_improvements\": \"[Any suggestions for improving the question]\"\n"
            f"}}\n\n"
            f"QUESTION TO EVALUATE:\n"
            f"Question: {test_question}\n"
            f"Correct Answer: {test_answer}\n"
            f"Explanation: {test_explanation}\n\n"
            f"Provide ONLY the JSON response, no additional text."
        )
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a neuroscience assessment expert. Be strict and objective. Always respond with valid JSON only."},
                {"role": "user", "content": eval_prompt}
            ],
            temperature=0.3
        )
        
        evaluation_text = response.choices[0].message.content.strip()
        
        print("✅ Rating generated successfully!")
        print("\n📝 Generated Rating:")
        print("-" * 30)
        print(evaluation_text)
        print("-" * 30)
        
        # Try to parse as JSON
        try:
            # Clean up the response to extract JSON
            evaluation_text = evaluation_text.strip()
            if evaluation_text.startswith("```json"):
                evaluation_text = evaluation_text[7:]
            if evaluation_text.endswith("```"):
                evaluation_text = evaluation_text[:-3]
            evaluation_text = evaluation_text.strip()
            
            # Parse JSON
            evaluation_data = json.loads(evaluation_text)
            
            # Check if required fields are present
            required_fields = [
                "question_quality_rating", 
                "answer_correctness_rating",
                "question_quality_justification",
                "answer_correctness_justification",
                "overall_assessment",
                "difficulty_level",
                "suggested_improvements"
            ]
            
            missing_fields = [field for field in required_fields if field not in evaluation_data]
            
            if not missing_fields:
                print("✅ JSON format is correct!")
                print(f"📊 Question Quality: {evaluation_data['question_quality_rating']}/10")
                print(f"📊 Answer Correctness: {evaluation_data['answer_correctness_rating']}/10")
                print(f"📊 Difficulty: {evaluation_data['difficulty_level']}")
                return True
            else:
                print(f"❌ Missing fields: {missing_fields}")
                return False
                
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error generating ratings: {e}")
        return False

def check_stored_ratings():
    """Check if ratings are being stored in JSON files."""
    print("\n🔍 Checking Stored Ratings...")
    print("=" * 50)
    
    try:
        from supabase import create_client, Client
        
        SUPABASE_URL = os.getenv("SUPABASE_URL", "")
        SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY", "")
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            print("❌ Supabase credentials not found!")
            return False
        
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # List feedback files
        files = supabase.storage.from_("brain-bee-data").list("feedback")
        
        if not files:
            print("📁 No feedback files found yet")
            print("💡 Try answering some questions in the app first")
            return False
        
        print(f"📁 Found {len(files)} feedback files")
        
        # Check a few recent files for ratings
        recent_files = files[:3]  # Check last 3 files
        
        for file_info in recent_files:
            if file_info['name'].endswith('.json'):
                try:
                    response = supabase.storage.from_("brain-bee-data").download(f"feedback/{file_info['name']}")
                    if response:
                        feedback_data = json.loads(response.decode('utf-8'))
                        
                        print(f"\n📄 File: {file_info['name']}")
                        print(f"Question: {feedback_data.get('question', 'N/A')[:50]}...")
                        print(f"Category: {feedback_data.get('category', 'N/A')}")
                        print(f"Correct: {feedback_data.get('is_correct', 'N/A')}")
                        
                        evaluation = feedback_data.get('evaluation', '')
                        if evaluation:
                            print("✅ Evaluation found:")
                            print(evaluation[:200] + "..." if len(evaluation) > 200 else evaluation)
                        else:
                            print("❌ No evaluation found")
                            
                except Exception as e:
                    print(f"❌ Error reading file {file_info['name']}: {e}")
                    continue
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking stored ratings: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 Testing Rating System...")
    print("=" * 60)
    
    # Test rating generation
    generation_ok = test_rating_generation()
    
    # Check stored ratings
    storage_ok = check_stored_ratings()
    
    print("\n📊 Results:")
    print(f"Rating Generation: {'✅' if generation_ok else '❌'}")
    print(f"Rating Storage: {'✅' if storage_ok else '❌'}")
    
    if generation_ok and storage_ok:
        print("\n🎉 Rating system working correctly!")
        print("💡 Your JSON files should contain proper ratings")
    else:
        print("\n⚠️  Some issues with rating system")
        if not generation_ok:
            print("   - Rating generation failed")
        if not storage_ok:
            print("   - Rating storage needs attention")

if __name__ == "__main__":
    main() 