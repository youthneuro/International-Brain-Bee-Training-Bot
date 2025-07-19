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

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")

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
    """Save user data to Supabase for persistence across serverless invocations."""
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
        
        # Store user data in Supabase - include session_id in the JSON data
        data_with_session = {
            "session_id": session_id,
            "data": data
        }
        
        supabase.table("user_sessions").upsert({
            "session_data": data_with_session,
            "updated_at": "now()"
        }).execute()
        return True
    except Exception as e:
        app.logger.error(f"Failed to save user data: {e}")
        # Check if it's a space limit error
        if "space" in str(e).lower() or "quota" in str(e).lower() or "limit" in str(e).lower():
            app.logger.error("Supabase space limit reached - falling back to session-only storage")
            return False
        return False

def load_user_data():
    """Load user data from Supabase."""
    if not supabase:
        return {}
    
    try:
        # Get session ID for this user
        session_id = session.get('session_id')
        if not session_id:
            return {}  # No session ID means no data to load
        
        # Get session data for this specific session ID
        result = supabase.table("user_sessions").select("session_data").eq("session_data->session_id", session_id).order("updated_at", desc=True).limit(1).execute()
        if result.data:
            session_data = result.data[0]['session_data']
            return session_data.get('data', {})
        return {}
    except Exception as e:
        app.logger.error(f"Failed to load user data: {e}")
        return {}

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

def cleanup_old_sessions():
    """Clean up old sessions to free up space. (30 period)"""
    if not supabase:
        return
    
    try:
        # Delete sessions older than 30 days
        supabase.table("user_sessions").delete().lt("updated_at", "now() - interval '30 days'").execute()
        app.logger.info("Cleaned up old sessions")
    except Exception as e:
        app.logger.error(f"Failed to cleanup old sessions: {e}")

def get_storage_status():
    """Check storage status and return recommendations."""
    if not supabase:
        return {"status": "no_supabase", "message": "Supabase not configured"}
    
    try:
        # Get session count
        result = supabase.table("user_sessions").select("id").execute()
        session_count = len(result.data) if result.data else 0
        
        # Get feedback count
        feedback_result = supabase.table("feedback_scores").select("id").execute()
        feedback_count = len(feedback_result.data) if feedback_result.data else 0
        
        return {
            "status": "healthy",
            "sessions": session_count,
            "feedback_entries": feedback_count,
            "message": f"Storage healthy: {session_count} sessions, {feedback_count} feedback entries"
        }
    except Exception as e:
        return {"status": "error", "message": f"Storage check failed: {e}"}

# === Helper: Generate Brain Bee Question ===
def get_brain_bee_question(category, retry_count=0):
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

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a neuroscience expert creating Brain Bee competition questions. IMPORTANT: Randomly distribute correct answers across A, B, C, and D options. Do not favor any particular letter. Each question must be unique and challenging."},
            {"role": "system", "content": relevant_content},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,  # Increased randomness
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

# === Helper: Generate Explanation ===
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

# === Helper: Evaluate Answer ===
def evaluate_response(question, correct_answer, explanation):
    eval_prompt = (
        f"You are evaluating a neuroscience multiple-choice quiz question. "
        f"Please do two things:\n"
        f"1. Rate the quality of the question itself on a scale from 1 to 10 (where 1 = terrible, 10 = expert-level).\n"
        f"2. Rate how appropriate and correct the stated 'correct answer' is, from 1 to 10.\n\n"
        f"Use the following format exactly:\n"
        f"Question Score: [score from 1 to 10]\n"
        f"Answer Score: [score from 1 to 10]\n"
        f"Justification: [brief justification for both scores]\n\n"
        f"Here is the question:\n"
        f"{question}\n\n"
        f"Correct Answer: {correct_answer}\n"
        f"Explanation: {explanation}"
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a neuroscience assessment expert. Be strict and objective."},
            {"role": "user", "content": eval_prompt}
        ],
        temperature=0.3
    )

    return response.choices[0].message.content.strip() if response.choices[0].message.content else ""

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
    
    # Generate explanation only when user answers incorrectly
    if not correct:
        current_question = quiz_state.get('question', '')
        current_choices = quiz_state.get('choices', [])
        current_correct_answer = quiz_state.get('correct_answer', '')
        
        # Try to determine category from question content
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

    try:
        # Store feedback in Supabase (no user_id needed)
        if supabase:  # Only try to insert if Supabase is configured
            supabase.table("feedback_scores").insert({
                "question": quiz_state.get('question'),
                "user_answer": user_answer,
                "correct_answer": quiz_state.get('correct_answer'),
                "evaluation": evaluation_result
            }).execute()
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
        cleanup_old_sessions()
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
