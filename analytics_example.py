#!/usr/bin/env python3
"""
Example script showing how to use structured outputs for analytics and reporting.
This demonstrates how the new structured output system can be used for data analysis.
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
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

def get_feedback_analytics() -> Dict[str, Any]:
    """
    Get analytics data from the feedback JSON files in Supabase Storage.
    """
    try:
        # List all feedback files
        files = supabase.storage.from_("brain-bee-data").list("feedback")
        
        analytics = {
            "total_feedback": 0,
            "categories": {},
            "correct_answers": 0,
            "total_questions": 0
        }
        
        # Process each feedback file
        for file_info in files:
            if file_info['name'].endswith('.json'):
                try:
                    # Download and parse feedback file
                    response = supabase.storage.from_("brain-bee-data").download(f"feedback/{file_info['name']}")
                    if response:
                        feedback_data = json.loads(response.decode('utf-8'))
                        
                        analytics["total_feedback"] += 1
                        analytics["total_questions"] += 1
                        
                        if feedback_data.get("is_correct", False):
                            analytics["correct_answers"] += 1
                        
                        category = feedback_data.get("category", "Unknown")
                        if category not in analytics["categories"]:
                            analytics["categories"][category] = {
                                "total": 0,
                                "correct": 0
                            }
                        
                        analytics["categories"][category]["total"] += 1
                        if feedback_data.get("is_correct", False):
                            analytics["categories"][category]["correct"] += 1
                            
                except Exception as e:
                    print(f"Failed to process feedback file {file_info['name']}: {e}")
                    continue
        
        # Calculate percentages
        if analytics["total_questions"] > 0:
            analytics["overall_accuracy"] = (analytics["correct_answers"] / analytics["total_questions"]) * 100
        else:
            analytics["overall_accuracy"] = 0
            
        for category in analytics["categories"]:
            cat_data = analytics["categories"][category]
            if cat_data["total"] > 0:
                cat_data["accuracy"] = (cat_data["correct"] / cat_data["total"]) * 100
            else:
                cat_data["accuracy"] = 0
        
        return {
            "status": "success",
            "analytics": analytics
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get analytics: {e}",
            "analytics": {}
        }

def get_recent_feedback(limit: int = 10) -> Dict[str, Any]:
    """
    Get recent feedback entries from JSON files.
    """
    try:
        # List all feedback files
        files = supabase.storage.from_("brain-bee-data").list("feedback")
        
        feedback_entries = []
        
        # Process each feedback file and sort by timestamp
        for file_info in files:
            if file_info['name'].endswith('.json'):
                try:
                    response = supabase.storage.from_("brain-bee-data").download(f"feedback/{file_info['name']}")
                    if response:
                        feedback_data = json.loads(response.decode('utf-8'))
                        feedback_entries.append(feedback_data)
                except Exception as e:
                    print(f"Failed to process feedback file {file_info['name']}: {e}")
                    continue
        
        # Sort by timestamp (newest first) and limit results
        feedback_entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        recent_feedback = feedback_entries[:limit]
        
        return {
            "status": "success",
            "feedback": recent_feedback,
            "count": len(recent_feedback)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get recent feedback: {e}",
            "feedback": [],
            "count": 0
        }

def get_category_performance(category: str) -> Dict[str, Any]:
    """
    Get performance data for a specific category from JSON files.
    """
    try:
        # List all feedback files
        files = supabase.storage.from_("brain-bee-data").list("feedback")
        
        category_entries = []
        
        # Process each feedback file
        for file_info in files:
            if file_info['name'].endswith('.json'):
                try:
                    response = supabase.storage.from_("brain-bee-data").download(f"feedback/{file_info['name']}")
                    if response:
                        feedback_data = json.loads(response.decode('utf-8'))
                        if feedback_data.get("category") == category:
                            category_entries.append(feedback_data)
                except Exception as e:
                    print(f"Failed to process feedback file {file_info['name']}: {e}")
                    continue
        
        if category_entries:
            total_questions = len(category_entries)
            correct_answers = sum(1 for item in category_entries if item.get("is_correct", False))
            accuracy = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
            
            return {
                "status": "success",
                "category": category,
                "total_questions": total_questions,
                "correct_answers": correct_answers,
                "accuracy_percentage": round(accuracy, 2),
                "recent_questions": category_entries[:5]  # Last 5 questions
            }
        else:
            return {
                "status": "success",
                "category": category,
                "total_questions": 0,
                "correct_answers": 0,
                "accuracy_percentage": 0,
                "recent_questions": []
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get category performance: {e}",
            "category": category,
            "total_questions": 0,
            "correct_answers": 0,
            "accuracy_percentage": 0,
            "recent_questions": []
        }

def export_structured_data() -> Dict[str, Any]:
    """
    Export structured data from JSON files for external analysis.
    """
    try:
        # List all feedback files
        files = supabase.storage.from_("brain-bee-data").list("feedback")
        
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "total_records": 0,
            "categories": {},
            "performance_metrics": {
                "overall_accuracy": 0,
                "total_questions": 0,
                "correct_answers": 0,
                "evaluated_questions": 0
            }
        }
        
        # Process each feedback file
        for file_info in files:
            if file_info['name'].endswith('.json'):
                try:
                    response = supabase.storage.from_("brain-bee-data").download(f"feedback/{file_info['name']}")
                    if response:
                        feedback_data = json.loads(response.decode('utf-8'))
                        
                        export_data["total_records"] += 1
                        export_data["performance_metrics"]["total_questions"] += 1
                        
                        if feedback_data.get("is_correct", False):
                            export_data["performance_metrics"]["correct_answers"] += 1
                        
                        if feedback_data.get("evaluation"):
                            export_data["performance_metrics"]["evaluated_questions"] += 1
                        
                        category = feedback_data.get("category", "Unknown")
                        if category not in export_data["categories"]:
                            export_data["categories"][category] = {
                                "total": 0,
                                "correct": 0,
                                "questions": []
                            }
                        
                        export_data["categories"][category]["total"] += 1
                        if feedback_data.get("is_correct", False):
                            export_data["categories"][category]["correct"] += 1
                        
                        # Add question to category
                        export_data["categories"][category]["questions"].append({
                            "question": feedback_data.get("question", ""),
                            "user_answer": feedback_data.get("user_answer", ""),
                            "correct_answer": feedback_data.get("correct_answer", ""),
                            "is_correct": feedback_data.get("is_correct", False),
                            "evaluation": feedback_data.get("evaluation", ""),
                            "timestamp": feedback_data.get("timestamp", "")
                        })
                        
                except Exception as e:
                    print(f"Failed to process feedback file {file_info['name']}: {e}")
                    continue
        
        # Calculate overall accuracy
        if export_data["performance_metrics"]["total_questions"] > 0:
            export_data["performance_metrics"]["overall_accuracy"] = (
                export_data["performance_metrics"]["correct_answers"] / 
                export_data["performance_metrics"]["total_questions"]
            ) * 100
        
        # Calculate category accuracies
        for category in export_data["categories"]:
            cat_data = export_data["categories"][category]
            if cat_data["total"] > 0:
                cat_data["accuracy"] = (cat_data["correct"] / cat_data["total"]) * 100
            else:
                cat_data["accuracy"] = 0
        
        return {
            "status": "success",
            "export_data": export_data
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to export data: {e}",
            "export_data": {}
        }

def main():
    """
    Main function to demonstrate analytics capabilities.
    """
    print("🧠 Brain Bee Training Bot - Analytics Report")
    print("=" * 50)
    
    # Get overall analytics
    print("\n📊 Overall Analytics:")
    analytics_result = get_feedback_analytics()
    
    if analytics_result["status"] == "success":
        analytics = analytics_result["analytics"]
        print(f"Total Questions: {analytics['total_questions']}")
        print(f"Correct Answers: {analytics['correct_answers']}")
        print(f"Overall Accuracy: {analytics.get('overall_accuracy', 0):.2f}%")
        
        print("\n📈 Performance by Category:")
        for category, data in analytics["categories"].items():
            print(f"  {category}: {data['total']} questions, {data['correct']} correct ({data.get('accuracy', 0):.2f}%)")
    else:
        print(f"❌ Error getting analytics: {analytics_result.get('message', 'Unknown error')}")
    
    # Get recent feedback
    print("\n🕒 Recent Feedback:")
    recent_result = get_recent_feedback(5)
    
    if recent_result["status"] == "success":
        for i, feedback in enumerate(recent_result["feedback"], 1):
            print(f"  {i}. {feedback.get('question', 'No question')[:50]}...")
            print(f"     Answer: {feedback.get('user_answer', 'N/A')} | Correct: {feedback.get('correct_answer', 'N/A')}")
            print(f"     Result: {'✅' if feedback.get('is_correct') else '❌'}")
    else:
        print(f"❌ Error getting recent feedback: {recent_result.get('message', 'Unknown error')}")
    
    # Get category performance
    print("\n🎯 Category Performance (Sensory System):")
    category_result = get_category_performance("Sensory system")
    
    if category_result["status"] == "success":
        print(f"  Total Questions: {category_result['total_questions']}")
        print(f"  Correct Answers: {category_result['correct_answers']}")
        print(f"  Accuracy: {category_result['accuracy_percentage']:.2f}%")
    else:
        print(f"❌ Error getting category performance: {category_result.get('message', 'Unknown error')}")
    
    # Export data
    print("\n📤 Data Export:")
    export_result = export_structured_data()
    
    if export_result["status"] == "success":
        export_data = export_result["export_data"]
        print(f"  Total Records: {export_data['total_records']}")
        print(f"  Categories: {len(export_data['categories'])}")
        print(f"  Export timestamp: {export_data['export_timestamp']}")
        
        # Save to local file
        with open("brain_bee_analytics_export.json", "w") as f:
            json.dump(export_data, f, indent=2)
        print("  ✅ Data exported to brain_bee_analytics_export.json")
    else:
        print(f"❌ Error exporting data: {export_result.get('message', 'Unknown error')}")
    
    print("\n" + "=" * 50)
    print("✅ Analytics report completed!")

if __name__ == "__main__":
    main() 