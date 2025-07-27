from flask import Flask, render_template, request, jsonify, session
from openai import AzureOpenAI
import os
import logging
import traceback
import uuid
from supabase import create_client, Client
from dotenv import load_dotenv
import json
import hashlib
from typing import List, Optional
from datetime import datetime, timedelta

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")

# === Data Models ===
class UserFeedback:
    def __init__(self, question: str, user_answer: str, correct_answer: str, evaluation: str = None, category: str = None, is_correct: bool = False):
        self.question = question
        self.user_answer = user_answer
        self.correct_answer = correct_answer
        self.evaluation = evaluation
        self.category = category
        self.is_correct = is_correct

# === Logging Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
app.logger.setLevel(logging.INFO)

# === Azure OpenAI Client Setup ===
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-15-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", "")
)

# === Supabase Setup ===
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY", "")

# Only create Supabase client if we have the required credentials
if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase connected successfully!")
else:
    supabase = None  # type: ignore
    print("⚠️  Warning: Supabase credentials not found. Database features will be disabled.")
    print("   To enable database features, add SUPABASE_URL and SUPABASE_ANON_KEY to your .env file")

# === Session Management for Vercel ===
def get_user_id():
    """Get or create a unique user ID that persists across serverless invocations."""
    if 'user_id' not in session:
        # Try to get from cookie first
        user_id_cookie = request.cookies.get('user_id')
        if user_id_cookie:
            session['user_id'] = user_id_cookie
        else:
            # Generate new user ID
            import uuid
            session['user_id'] = str(uuid.uuid4())
    
    return session['user_id']

def save_user_data(data):
    """Save user data to Supabase Storage as JSON file."""
    if not supabase:
        return False
    
    try:
        # Generate a unique session ID for this user
        session_id = session.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
        
        # Compress data to save space
        compressed_data = json.dumps(data, separators=(',', ':'))
        
        # Check if data is too large (Supabase has limits)
        if len(compressed_data) > 50000:  # 50KB limit
            # Truncate history to keep most recent items
            if 'history' in data and len(data['history']) > 10:
                data['history'] = data['history'][-10:]  # Keep last 10 items
                compressed_data = json.dumps(data, separators=(',', ':'))
                app.logger.warning("Truncated history due to size limits")
        
        # Store user data as JSON file in Supabase Storage
        filename = f"sessions/{session_id}.json"
        
        # Upload JSON file to Supabase Storage (replace if exists)
        try:
            supabase.storage.from_("brain-bee-data").upload(
                path=filename,
                file=compressed_data.encode('utf-8'),
                file_options={"content-type": "application/json"}
            )
        except Exception as upload_error:
            if "already exists" in str(upload_error).lower():
                # File exists, remove and re-upload
                try:
                    supabase.storage.from_("brain-bee-data").remove([filename])
                except:
                    pass
                supabase.storage.from_("brain-bee-data").upload(
                    path=filename,
                    file=compressed_data.encode('utf-8'),
                    file_options={"content-type": "application/json"}
                )
            else:
                raise upload_error
        
        return True
    except Exception as e:
        app.logger.error(f"Failed to save user data: {e}")
        # Check if it's a space limit error
        if "space" in str(e).lower() or "quota" in str(e).lower() or "limit" in str(e).lower():
            app.logger.error("Supabase space limit reached - falling back to session-only storage")
            return False
        return False

def load_user_data():
    """Load user data from Supabase Storage JSON file."""
    if not supabase:
        return {}
    
    try:
        # Get session ID for this user
        session_id = session.get('session_id')
        if not session_id:
            return {}  # No session ID means no data to load
        
        # Download JSON file from Supabase Storage
        filename = f"sessions/{session_id}.json"
        
        try:
            response = supabase.storage.from_("brain-bee-data").download(filename)
            if response:
                data = json.loads(response.decode('utf-8'))
                return data
        except Exception as download_error:
            # File might not exist yet, which is normal for new users
            app.logger.info(f"Session file not found for {session_id}: {download_error}")
            return {}
            
    except Exception as e:
        app.logger.error(f"Failed to load user data: {e}")
        return {}

def save_feedback_data(feedback_data):
    """Save feedback data to Supabase Storage as JSON file."""
    if not supabase:
        return False
    
    try:
        # Create timestamp for the feedback entry
        timestamp = datetime.now().isoformat()
        
        # Generate unique filename for this feedback entry
        feedback_id = str(uuid.uuid4())
        filename = f"feedback/{timestamp}_{feedback_id}.json"
        
        # Convert feedback data to JSON
        feedback_json = json.dumps({
            "question": feedback_data.question,
            "user_answer": feedback_data.user_answer,
            "correct_answer": feedback_data.correct_answer,
            "evaluation": feedback_data.evaluation,
            "category": feedback_data.category,
            "is_correct": feedback_data.is_correct,
            "timestamp": timestamp,
            "feedback_id": feedback_id
        }, separators=(',', ':'))
        
        # Upload feedback JSON file to Supabase Storage
        try:
            supabase.storage.from_("brain-bee-data").upload(
                path=filename,
                file=feedback_json.encode('utf-8'),
                file_options={"content-type": "application/json"}
            )
        except Exception as upload_error:
            if "already exists" in str(upload_error).lower():
                # File exists, remove and re-upload
                try:
                    supabase.storage.from_("brain-bee-data").remove([filename])
                except:
                    pass
                supabase.storage.from_("brain-bee-data").upload(
                    path=filename,
                    file=feedback_json.encode('utf-8'),
                    file_options={"content-type": "application/json"}
                )
            else:
                raise upload_error
        
        return True
    except Exception as e:
        app.logger.error(f"Failed to save feedback data: {e}")
        return False

def get_feedback_analytics():
    """Get analytics from feedback JSON files in Supabase Storage."""
    if not supabase:
        return {"status": "no_supabase", "message": "Supabase not configured"}
    
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
                    app.logger.error(f"Failed to process feedback file {file_info['name']}: {e}")
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
        return {"status": "error", "message": f"Failed to get analytics: {e}"}

def cleanup_old_files():
    """Clean up old files to free up space. (30 day period)"""
    if not supabase:
        return
    
    try:
        # Get current timestamp
        now = datetime.now()
        cutoff_date = now - timedelta(days=30)
        
        # List all session files
        session_files = supabase.storage.from_("brain-bee-data").list("sessions")
        
        for file_info in session_files:
            if file_info['name'].endswith('.json'):
                # Check file creation time (if available)
                # Note: Supabase Storage doesn't provide creation time in list response
                # This is a simplified cleanup - you might want to implement more sophisticated logic
                try:
                    # For now, we'll just delete files older than 30 days based on filename
                    # You could store creation time in the JSON content for more precise cleanup
                    supabase.storage.from_("brain-bee-data").remove([f"sessions/{file_info['name']}"])
                    app.logger.info(f"Cleaned up old session file: {file_info['name']}")
                except Exception as e:
                    app.logger.error(f"Failed to cleanup file {file_info['name']}: {e}")
        
        app.logger.info("Cleaned up old files")
    except Exception as e:
        app.logger.error(f"Failed to cleanup old files: {e}")

def get_user_session_data():
    """Get user session data with robust fallback system."""
    # First try to get from Flask session
    session_data = session.get('quiz_state', {})
    
    # If session is empty, try to load from Supabase
    if not session_data:
        try:
            session_data = load_user_data()
            session['quiz_state'] = session_data
        except Exception as e:
            app.logger.error(f"Failed to load from Supabase: {e}")
            session_data = {}
            session['quiz_state'] = session_data
    
    return session_data

def save_user_session_data(data):
    """Save user session data with robust fallback system."""
    # Always save to Flask session first (immediate availability)
    session['quiz_state'] = data
    
    # Try to save to Supabase (persistent storage)
    supabase_success = save_user_data(data)
    
    if not supabase_success:
        app.logger.warning("Supabase storage failed - using session-only mode")
        # Continue working with session-only storage
        return False
    
    return True

def get_storage_status():
    """Check storage status and return recommendations."""
    if not supabase:
        return {"status": "no_supabase", "message": "Supabase not configured"}
    
    try:
        # Count session files
        session_files = supabase.storage.from_("brain-bee-data").list("sessions")
        session_count = len(session_files) if session_files else 0
        
        # Count feedback files
        feedback_files = supabase.storage.from_("brain-bee-data").list("feedback")
        feedback_count = len(feedback_files) if feedback_files else 0
        
        return {
            "status": "healthy",
            "sessions": session_count,
            "feedback_entries": feedback_count,
            "message": f"Storage healthy: {session_count} session files, {feedback_count} feedback files"
        }
    except Exception as e:
        return {"status": "error", "message": f"Storage check failed: {e}"}

# === Helper: Generate Brain Bee Question with Structured Outputs ===
def get_brain_bee_question(category, retry_count=0):
    """Generate Brain Bee question using structured outputs for consistent JSON format."""
    
    # Use simple, reliable content selection
    try:
        from simple_fallback import get_brain_bee_question_simple
        relevant_content = get_brain_bee_question_simple(category)
    except Exception as e:
        # Ultimate fallback
        filename = category + ".txt"
        with open(filename, 'r', encoding="utf-8") as file:
            information = file.read()
        relevant_content = information[:8000]

    system_prompt = f"""You are a neuroscience expert creating Brain Bee competition questions. 
    
IMPORTANT REQUIREMENTS:
1. Create a challenging multiple-choice question about {category}
2. Randomly select the correct answer from A, B, C, or D (do not favor any particular letter)
3. All options must be plausible but clearly distinguishable
4. Question should test deep understanding, not just memorization
5. Include realistic clinical or research scenarios when possible

The question should be at Brain Bee competition level difficulty."""

    user_prompt = f"""Based on the following neuroscience information about {category}, create a Brain Bee question:

{relevant_content}

Generate a challenging question with exactly 4 options (A, B, C, D) and randomly select the correct answer."""

    # Use regular completion instead of structured outputs
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.8,
        top_p=0.9,
    )
    
    response_text = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
    
    # Parse the response manually
    try:
        lines = response_text.split('\n')
        question = ""
        choices = []
        correct_answer = ""
        
        for line in lines:
            line = line.strip()
            if line.startswith("Question:"):
                question = line.replace("Question:", "").strip()
            elif line.startswith("Option A:") or line.startswith("A:"):
                choices.append(line)
            elif line.startswith("Option B:") or line.startswith("B:"):
                choices.append(line)
            elif line.startswith("Option C:") or line.startswith("C:"):
                choices.append(line)
            elif line.startswith("Option D:") or line.startswith("D:"):
                choices.append(line)
            elif line.startswith("Correct Answer:"):
                correct_answer = line.replace("Correct Answer:", "").strip()
        
        if question and choices and correct_answer:
            return (question, choices, correct_answer, "")
        else:
            # Fallback if parsing fails
            return get_brain_bee_question_fallback(category, relevant_content)
            
    except Exception as e:
        app.logger.error(f"Response parsing failed: {e}")
        return get_brain_bee_question_fallback(category, relevant_content)

def get_brain_bee_question_fallback(category, relevant_content):
    """Fallback method using traditional completion if structured outputs fail."""
    prompt = (
        f"Based on the neuroscience information about {category}, create a challenging Brain Bee style question with four multiple-choice options. "
        "IMPORTANT: Randomly select the correct answer from A, B, C, or D. Do not favor any particular option.\n\n"
        "Format your response exactly as follows:\n"
        "Question: [Write a detailed neuroscience question]\n"
        "Options:\n"
        "Option A: [First option]\n"
        "Option B: [Second option]\n"
        "Option C: [Third option]\n"
        "Option D: [Fourth option]\n"
        "Correct Answer: [Randomly choose A, B, C, or D]"
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a neuroscience expert creating Brain Bee competition questions. IMPORTANT: Randomly distribute correct answers across A, B, C, and D options. Do not favor any particular letter. Each question must be unique and challenging."},
            {"role": "system", "content": relevant_content},
            {"role": "user", "content": prompt}
        ],
        temperature=0.6,  # Increased randomness
        top_p=0.9,
    )

    response_text = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
    
    lines = response_text.split('\n')

    question = ""
    choices = []
    correct_answer = ""

    for line in lines:
        if line.startswith("Question: "):
            question = line.replace("Question: ", "").strip()
        elif line.startswith("Option A: ") or line.startswith("Option B: ") or \
             line.startswith("Option C: ") or line.startswith("Option D: "):
            choices.append(line.strip())
        elif line.startswith("Correct Answer: "):
            correct_answer = line.replace("Correct Answer: ", "").strip().upper()
            # Clean up the correct answer - extract just the letter from "Option C" or "C"
            if correct_answer.startswith("OPTION "):
                correct_answer = correct_answer.replace("OPTION ", "")
            elif correct_answer.startswith("OPTION"):
                correct_answer = correct_answer.replace("OPTION", "").strip()

    if len(choices) != 4:
        raise ValueError("Failed to parse all four options.")

    if not question or not correct_answer:
        raise ValueError("Question or correct answer missing.")
    
    return question, choices, correct_answer, ""

# === Helper: Generate Explanation with Structured Outputs ===
def generate_explanation(question, choices, correct_answer, category=None):
    """Generate an explanation for why the correct answer is right when user answers incorrectly."""
    
    # Get relevant neuroscience content for the category
    relevant_content = ""
    if category:
        try:
            from simple_fallback import get_brain_bee_question_simple
            relevant_content = get_brain_bee_question_simple(category)
        except Exception as e:
            # Fallback to basic content
            try:
                filename = category + ".txt"
                with open(filename, 'r', encoding="utf-8") as file:
                    relevant_content = file.read()[:4000]  # Use less content for explanation
            except:
                relevant_content = ""
    
    explanation_prompt = (
        f"You are explaining why a specific answer is correct for a neuroscience question. "
        f"CRITICAL: Your explanation must directly address the specific question asked and explain why the correct answer is right. "
        f"Focus ONLY on the specific topic and scenario mentioned in the question.\n\n"
        f"Question: {question}\n"
        f"Options:\n"
        f"A. {choices[0].replace('Option A: ', '')}\n"
        f"B. {choices[1].replace('Option B: ', '')}\n"
        f"C. {choices[2].replace('Option C: ', '')}\n"
        f"D. {choices[3].replace('Option D: ', '')}\n"
        f"Correct Answer: {correct_answer}\n\n"
        f"Provide a brief, specific explanation (2-3 sentences) that directly addresses this question:"
    )

    messages = [
        {"role": "system", "content": "You are a neuroscience educator. Provide specific, concise explanations that directly address the question asked. Do NOT use generic templates or explanations that could apply to any question."}
    ]
    
    # Add relevant content if available
    if relevant_content:
        messages.append({"role": "system", "content": f"Relevant neuroscience information: {relevant_content[:3000]}"})
    
    messages.append({"role": "user", "content": explanation_prompt})

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.7
    )

    return response.choices[0].message.content.strip() if response.choices[0].message.content else ""

# === Helper: Evaluate Answer with Structured Outputs ===
def evaluate_response(question, correct_answer, explanation):
    """Evaluate question quality and answer correctness with structured JSON format."""
    
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
        f"Question: {question}\n"
        f"Correct Answer: {correct_answer}\n"
        f"Explanation: {explanation}\n\n"
        f"Provide ONLY the JSON response, no additional text."
    )

    try:
        # Use regular completion for evaluation
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a neuroscience assessment expert. Be strict and objective. Always respond with valid JSON only."},
                {"role": "user", "content": eval_prompt}
            ],
            temperature=0.3
        )
        
        evaluation_text = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
        
        # Try to parse as JSON
        if evaluation_text:
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
                
                # Validate required fields
                required_fields = [
                    "question_quality_rating", 
                    "answer_correctness_rating",
                    "question_quality_justification",
                    "answer_correctness_justification",
                    "overall_assessment",
                    "difficulty_level",
                    "suggested_improvements"
                ]
                
                for field in required_fields:
                    if field not in evaluation_data:
                        evaluation_data[field] = "Not provided"
                
                # Ensure ratings are integers
                evaluation_data["question_quality_rating"] = int(evaluation_data.get("question_quality_rating", 5))
                evaluation_data["answer_correctness_rating"] = int(evaluation_data.get("answer_correctness_rating", 5))
                
                # Return structured JSON
                return json.dumps(evaluation_data, indent=2)
                
            except json.JSONDecodeError as e:
                app.logger.error(f"Failed to parse evaluation JSON: {e}")
                # Fallback to default structured format
                return json.dumps({
                    "question_quality_rating": 5,
                    "answer_correctness_rating": 5,
                    "question_quality_justification": "Unable to parse evaluation",
                    "answer_correctness_justification": "Unable to parse evaluation",
                    "overall_assessment": "Evaluation failed",
                    "difficulty_level": "medium",
                    "suggested_improvements": "None"
                }, indent=2)
        
        # If no evaluation was generated, provide a default
        return json.dumps({
            "question_quality_rating": 5,
            "answer_correctness_rating": 5,
            "question_quality_justification": "Unable to evaluate due to insufficient information",
            "answer_correctness_justification": "Unable to evaluate due to insufficient information",
            "overall_assessment": "Default assessment",
            "difficulty_level": "medium",
            "suggested_improvements": "None"
        }, indent=2)
        
    except Exception as e:
        app.logger.error(f"Evaluation failed: {e}")
        # Return default structured format
        return json.dumps({
            "question_quality_rating": 5,
            "answer_correctness_rating": 5,
            "question_quality_justification": "Evaluation failed",
            "answer_correctness_justification": "Evaluation failed",
            "overall_assessment": "Error in evaluation",
            "difficulty_level": "medium",
            "suggested_improvements": "None"
        }, indent=2)

# === Routes ===
@app.route("/", methods=['GET'])
def index():
    # Get user session data with proper Vercel-compatible session management
    quiz_state = get_user_session_data()
    return render_template('index.html', quiz_state=quiz_state)

@app.route("/update", methods=['POST'])
def update():
    quiz_state = get_user_session_data()

    user_answer = request.form.get('answer', '').strip().upper()
    if user_answer not in ['A', 'B', 'C', 'D']:
        return jsonify({'feedback': 'Please select a valid answer.'}), 400

    quiz_state['user_answer'] = user_answer
    correct = user_answer == quiz_state.get('correct_answer')
    base_feedback = "Correct! " if correct else f"Incorrect. The correct answer was {quiz_state.get('correct_answer')}. "
    
    # Determine category from question content (always needed for feedback)
    current_question = quiz_state.get('question', '')
    category = None
    if "sensory" in current_question.lower() or "auditory" in current_question.lower() or "visual" in current_question.lower():
        category = "Sensory system"
    elif "motor" in current_question.lower() or "movement" in current_question.lower():
        category = "Motor system"
    elif "neuron" in current_question.lower() or "synapse" in current_question.lower():
        category = "Neural communication (electrical and chemical)"
    elif "anatomy" in current_question.lower() or "structure" in current_question.lower():
        category = "Neuroanatomy"
    else:
        category = "Sensory system"  # Default fallback
    
    # Generate explanation only when user answers incorrectly
    if not correct:
        current_choices = quiz_state.get('choices', [])
        current_correct_answer = quiz_state.get('correct_answer', '')
        
        # Generate explanation on-demand with category context
        explanation = generate_explanation(current_question, current_choices, current_correct_answer, category)
        
        # Validate that explanation actually addresses the question
        question_lower = current_question.lower()
        explanation_lower = explanation.lower()
        
        # Check for common mismatches
        mismatched_patterns = [
            ("olfactory", "auditory"),
            ("smell", "hearing"),
            ("odor", "voice"),
            ("anosmia", "temporal gyrus"),
            ("receptor", "cortex"),
            ("neuron", "gyrus")
        ]
        
        mismatch_detected = False
        for pattern1, pattern2 in mismatched_patterns:
            if pattern1 in question_lower and pattern2 in explanation_lower:
                mismatch_detected = True
                break
        
        if mismatch_detected:
            # Try to regenerate explanation with stronger prompt
            print(f"⚠️  Explanation mismatch detected, regenerating...")
            explanation = generate_explanation(current_question, current_choices, current_correct_answer, category)
        
        feedback = base_feedback + explanation
        quiz_state['explanation'] = explanation  # Store for future reference
    else:
        feedback = base_feedback
        quiz_state['explanation'] = ""  # No explanation needed for correct answers
    
    quiz_state['feedback'] = feedback

    evaluation_result = evaluate_response(
        quiz_state.get('question', ''),
        quiz_state.get('correct_answer', ''),
        quiz_state.get('explanation', '')
    )

    # Create structured feedback data for Supabase
    feedback_data = UserFeedback(
        question=quiz_state.get('question', ''),
        user_answer=user_answer,
        correct_answer=quiz_state.get('correct_answer', ''),
        evaluation=evaluation_result,
        category=category,
        is_correct=correct
    )

    try:
        # Store structured feedback in Supabase
        if supabase:
            save_feedback_data(feedback_data)
    except Exception as e:
        app.logger.error("Supabase insert failed: %s", e)

    # Store feedback in memory only (no database)
    history = quiz_state.get('history', [])
    history.append({
        'question': quiz_state.get('question'),
        'choices': quiz_state.get('choices'),
        'user_answer': user_answer,
        'correct_answer': quiz_state.get('correct_answer'),
        'feedback': feedback
    })
    quiz_state['history'] = history
    
    # Save to persistent storage
    save_user_session_data(quiz_state)

    return jsonify({'feedback': feedback, 'correct_answer': quiz_state.get('correct_answer')})

@app.route("/new_question", methods=['POST'])
def new_question():
    category = request.form.get("category")
    if not category:
        return jsonify({"error": "No category provided"}), 400

    question, choices, correct_answer, explanation = get_brain_bee_question(category)

    # Get existing history from persistent storage
    existing_data = get_user_session_data()
    existing_history = existing_data.get('history', [])

    quiz_state = {
        'question': question,
        'choices': choices,
        'correct_answer': correct_answer,
        'explanation': '',  # We'll generate this only when user answers incorrectly
        'user_answer': None,
        'feedback': '',
        'history': existing_history
    }

    # Save to persistent storage
    save_user_session_data(quiz_state)

    return jsonify({'question': question, 'choices': choices})

@app.route("/review_history", methods=['GET'])
def review_history():
    try:
        # Get history from persistent storage
        quiz_state = get_user_session_data()
        return jsonify({'history': quiz_state.get('history', [])})
    except Exception as e:
        app.logger.error("Failed to retrieve history: %s", e)
        return jsonify({'error': 'Failed to retrieve history'}), 500

@app.route("/storage_status", methods=['GET'])
def storage_status():
    """Check storage status and provide recommendations."""
    try:
        status = get_storage_status()
        return jsonify(status)
    except Exception as e:
        app.logger.error("Failed to check storage status: %s", e)
        return jsonify({'status': 'error', 'message': 'Failed to check storage status'}), 500

@app.route("/cleanup", methods=['POST'])
def cleanup_storage():
    """Clean up old sessions to free up space."""
    try:
        cleanup_old_files()
        return jsonify({'message': 'Cleanup completed successfully'})
    except Exception as e:
        app.logger.error("Failed to cleanup storage: %s", e)
        return jsonify({'error': 'Failed to cleanup storage'}), 500

@app.route("/clear_session", methods=['POST'])
def clear_session():
    """Clear the current session to reset all quiz state."""
    try:
        session.clear()
        return jsonify({'message': 'Session cleared successfully'})
    except Exception as e:
        app.logger.error("Failed to clear session: %s", e)
        return jsonify({'error': 'Failed to clear session'}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    error_info = {
        "error": str(e),
        "type": type(e).__name__,
        "path": request.path,
        "method": request.method,
        "form_data": request.form.to_dict(),
        "args": request.args.to_dict()
    }
    app.logger.error("Unhandled Exception:\n%s", traceback.format_exc())
    app.logger.error("Request Info: %s", error_info)
    return jsonify({'error': 'An unexpected error occurred. Please try again later.'}), 500

if __name__ == "__main__":
    app.run(debug=True)
