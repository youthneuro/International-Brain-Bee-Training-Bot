from flask import Flask, render_template, request, jsonify, session
from openai import AzureOpenAI
import os
import logging
import traceback
from supabase import create_client, Client

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")

# === Logging Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
app.logger.setLevel(logging.INFO)

# === Azure OpenAI Client Setup ===
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-15-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

# === Supabase Setup ===
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# === Helper: Generate Brain Bee Question ===
def get_brain_bee_question(category):
    prompt = (
        f"Based on the neuroscience information about {category} you have been fed in, provide a difficult Brain Bee style question asking about a hypothetical situation with four multiple-choice options. "
        "Include the correct answer and an explanation for the answer. "
        "Format the output as follows:\n"
        "Question: [Question Text]\n"
        "Options:\n"
        "Option A: [Option A Text]\n"
        "Option B: [Option B Text]\n"
        "Option C: [Option C Text]\n"
        "Option D: [Option D Text]\n"
        "Correct Answer: [A/B/C/D]\n"
        "Explanation: [Explanation Text]"
    )

    filename = category + ".txt"
    with open(filename, 'r', encoding="utf-8") as file:
        information = file.read()

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a neuroscience expert with years of experience with writing brain bee questions. You also have a very high understanding of neuroscience pedagogy and how to properly write neuroscience competition exam questions."},
            {"role": "system", "content": information[:10000]},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        top_p=0.9,
    )

    response_text = response.choices[0].message.content.strip()
    lines = response_text.split('\n')

    question = ""
    choices = []
    correct_answer = ""
    explanation = ""

    for line in lines:
        if line.startswith("Question: "):
            question = line.replace("Question: ", "").strip()
        elif line.startswith("Option A: ") or line.startswith("Option B: ") or \
             line.startswith("Option C: ") or line.startswith("Option D: "):
            choices.append(line.strip())
        elif line.startswith("Correct Answer: "):
            correct_answer = line.replace("Correct Answer: ", "").strip().upper()
        elif line.startswith("Explanation: "):
            explanation = line.replace("Explanation: ", "").strip()

    if len(choices) != 4:
        raise ValueError("Failed to parse all four options.")

    return question, choices, correct_answer, explanation

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

    return response.choices[0].message.content.strip()

# === Routes ===
@app.route("/", methods=['GET'])
def index():
    quiz_state = session.get('quiz_state', {})
    return render_template('index.html', quiz_state=quiz_state)

@app.route("/update", methods=['POST'])
def update():
    quiz_state = session.get('quiz_state', {})

    user_answer = request.form.get('answer', '').strip().upper()
    if user_answer not in ['A', 'B', 'C', 'D']:
        return jsonify({'feedback': 'Please select a valid answer.'}), 400

    quiz_state['user_answer'] = user_answer
    correct = user_answer == quiz_state.get('correct_answer')
    base_feedback = "Correct! " if correct else f"Incorrect. The correct answer was {quiz_state.get('correct_answer')}. "
    feedback = base_feedback + quiz_state.get('explanation', '')
    quiz_state['feedback'] = feedback

    evaluation_result = evaluate_response(
        quiz_state.get('question', ''),
        quiz_state.get('correct_answer', ''),
        quiz_state.get('explanation', '')
    )

    try:
        supabase.table("feedback_scores").insert({
            "question": quiz_state.get('question'),
            "user_answer": user_answer,
            "correct_answer": quiz_state.get('correct_answer'),
            "evaluation": evaluation_result
        }).execute()
    except Exception as e:
        app.logger.error("Supabase insert failed: %s", e)

    history = quiz_state.get('history', [])
    history.append({
        'question': quiz_state.get('question'),
        'choices': quiz_state.get('choices'),
        'user_answer': user_answer,
        'correct_answer': quiz_state.get('correct_answer'),
        'feedback': feedback
    })
    quiz_state['history'] = history
    session['quiz_state'] = quiz_state

    return jsonify({'feedback': feedback})

@app.route("/new_question", methods=['POST'])
def new_question():
    category = request.form.get("category")
    if not category:
        return jsonify({"error": "No category provided"}), 400

    question, choices, correct_answer, explanation = get_brain_bee_question(category)

    quiz_state = {
        'question': question,
        'choices': choices,
        'correct_answer': correct_answer,
        'explanation': explanation,
        'user_answer': None,
        'feedback': '',
        'history': session.get('quiz_state', {}).get('history', [])
    }

    session['quiz_state'] = quiz_state

    return jsonify({'question': question, 'choices': choices})

@app.route("/review_history", methods=['GET'])
def review_history():
    return jsonify({'history': session.get('quiz_state', {}).get('history', [])})

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
