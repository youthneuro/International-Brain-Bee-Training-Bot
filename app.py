from flask import Flask, render_template, request, jsonify
import openai
import os
import logging
import traceback

app = Flask(__name__)

# === Logging Setup ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
app.logger.setLevel(logging.INFO)

# === OpenAI API Setup ===
openai.api_type = "azure"
openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_version = "2024-02-15-preview"

quiz_state = {
    'question': '',
    'choices': [],
    'correct_answer': '',
    'explanation': '',
    'user_answer': None,
    'feedback': '',
    'history': []
}

# === Helper: Generate Question ===
def get_brain_bee_question(category):
    prompt = (
        "Based on the neuroscience information about " + category + " you have been fed in, provide a difficult Brain Bee style question asking about a hypothetical situation with four multiple-choice options. "
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

    response = openai.ChatCompletion.create(
        engine='gpt-4o',
        messages=[
            {"role": "system", "content": "You are a neuroscience expert with years of experience with writing brain bee questions. You also have a very high understanding of neuroscience pedagogy and how to properly write neuroscience competition exam questions."},
            {"role": "system", "content": information[:10000]},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        top_p=0.9,
    )

    response_text = response.choices[0].message['content'].strip()
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

@app.route("/", methods=['GET'])
def index():
    return render_template('index.html', quiz_state=quiz_state)

@app.route("/update", methods=['POST'])
def update():
    user_answer = request.form.get('answer', '').strip().upper()
    if user_answer not in ['A', 'B', 'C', 'D']:
        return jsonify({'feedback': 'Please select a valid answer.'}), 400

    quiz_state['user_answer'] = user_answer

    if user_answer == quiz_state['correct_answer']:
        quiz_state['feedback'] = "Correct! " + quiz_state['explanation']
    else:
        quiz_state['feedback'] = f"Incorrect. The correct answer was {quiz_state['correct_answer']}. " + quiz_state['explanation']

    quiz_state['history'].append({
        'question': quiz_state['question'],
        'choices': quiz_state['choices'],
        'user_answer': user_answer,
        'correct_answer': quiz_state['correct_answer'],
        'feedback': quiz_state['feedback']
    })

    return jsonify({'feedback': quiz_state['feedback']})

@app.route("/new_question", methods=['POST'])
def new_question():
    category = request.form.get("category")
    if not category:
        return jsonify({"error": "No category provided"}), 400

    question, choices, correct_answer, explanation = get_brain_bee_question(category)
    quiz_state.update({
        'question': question,
        'choices': choices,
        'correct_answer': correct_answer,
        'explanation': explanation,
        'user_answer': None,
        'feedback': ''
    })

    return jsonify({'question': question, 'choices': choices})

@app.route("/review_history", methods=['GET'])
def review_history():
    return jsonify({'history': quiz_state['history']})

# === Global Error Handler ===
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
