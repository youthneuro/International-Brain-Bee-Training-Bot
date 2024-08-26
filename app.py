from flask import Flask, render_template, request, jsonify
import openai
import os

app = Flask(__name__)

# Configure OpenAI to use Azure
openai.api_type = "azure"
openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")  # The endpoint URL
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")    # The API key
openai.api_version = "2024-02-15-preview"  # The API version

# Global state to manage quiz state and history
quiz_state = {
    'question': '',
    'choices': [],
    'correct_answer': '',
    'explanation': '',
    'user_answer': None,
    'feedback': '',
    'history': []  # Add history to track user responses
}

def get_brain_bee_question():
    prompt = ("Provide a difficult Brain Bee style question asking about a hypothetical situation with four multiple-choice options. "
              "Include the correct answer and an explanation for the answer. "
              "Format the output as follows:\n"
              "Question: [Question Text]\n"
              "Options:\n"
              "Option A: [Option A Text]\n"
              "Option B: [Option B Text]\n"
              "Option C: [Option C Text]\n"
              "Option D: [Option D Text]\n"
              "Correct Answer: [A/B/C/D]\n"
              "Explanation: [Explanation Text]")

    response = openai.ChatCompletion.create(
        engine='gpt-4o',  # Specify the Azure engine name for GPT-4
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,  # Set temperature for creativity
        top_p=0.9,        # Set top_p for diversity control
    )
    
    response_text = response.choices[0].message['content'].strip()
    lines = response_text.split('\n')
    
    question = lines[0].replace("Question: ", "").strip()
    choices = [line.replace("Option ", "").strip() for line in lines[3:7]]
    correct_answer = lines[6].replace("Correct Answer: ", "").strip()
    explanation = lines[7].replace("Explanation: ", "").strip()

    return question, choices, correct_answer, explanation

@app.route("/", methods=['GET'])
def index():
    global quiz_state

    # Generate an initial question and options
    quiz_state['question'], quiz_state['choices'], quiz_state['correct_answer'], quiz_state['explanation'] = get_brain_bee_question()
    quiz_state['feedback'] = ''
    
    # Render the HTML page with initial data
    return render_template('index.html', quiz_state=quiz_state)

@app.route("/update", methods=['POST'])
def update():
    global quiz_state

    user_answer = request.form.get('answer')
    quiz_state['user_answer'] = user_answer

    if user_answer == quiz_state['correct_answer']:
        quiz_state['feedback'] = "Correct! " + quiz_state['explanation']
    else:
        quiz_state['feedback'] = f"Incorrect. The correct answer was {quiz_state['correct_answer']}. " + quiz_state['explanation']

    # Update history
    quiz_state['history'].append({
        'question': quiz_state['question'],
        'choices': quiz_state['choices'],
        'user_answer': user_answer,
        'correct_answer': quiz_state['correct_answer'],
        'feedback': quiz_state['feedback']
    })

    return jsonify({
        'feedback': quiz_state['feedback']
    })

@app.route("/new_question", methods=['POST'])
def new_question():
    global quiz_state

    # Generate a new question for the next round
    quiz_state['question'], quiz_state['choices'], quiz_state['correct_answer'], quiz_state['explanation'] = get_brain_bee_question()
    
    return jsonify({
        'question': quiz_state['question'],
        'choices': quiz_state['choices']
    })

@app.route("/review_history", methods=['GET'])
def review_history():
    global quiz_state

    return jsonify({
        'history': quiz_state['history']
    })

if __name__ == "__main__":
    app.run(debug=True)
