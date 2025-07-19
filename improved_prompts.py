# Improved Prompt Engineering for Brain Bee Training Bot

def get_brain_bee_question_improved(category):
    """
    Improved prompt engineering with better structure, validation, and examples.
    """
    
    # Load category-specific content
    filename = category + ".txt"
    with open(filename, 'r', encoding="utf-8") as file:
        information = file.read()
    
    # Create semantic chunks (better than arbitrary truncation)
    chunks = create_semantic_chunks(information, max_chunk_size=8000)
    relevant_content = select_most_relevant_chunks(chunks, category)
    
    # Enhanced system prompt with examples
    system_prompt = f"""You are an expert neuroscience educator specializing in Brain Bee competition preparation. You have:
- 15+ years experience writing neuroscience competition questions
- Deep understanding of Brain Bee question patterns and difficulty levels
- Expertise in {category} specifically

Your task: Create a challenging Brain Bee-style multiple choice question.

CRITICAL REQUIREMENTS:
1. Question must test deep understanding, not memorization
2. Include a realistic clinical or research scenario
3. All distractors must be plausible but clearly incorrect
4. Explanation should teach the underlying concept
5. Difficulty level: Advanced (suitable for Brain Bee finalists)

EXAMPLE FORMAT:
Question: A 45-year-old patient presents with difficulty recognizing familiar faces but can identify objects normally. MRI reveals damage to the right fusiform gyrus. This condition is most likely:
Options:
Option A: Prosopagnosia
Option B: Visual agnosia  
Option C: Hemianopia
Option D: Balint syndrome
Correct Answer: A
Explanation: Prosopagnosia (face blindness) specifically affects face recognition while preserving object recognition. The fusiform gyrus contains the fusiform face area (FFA), which is specialized for face processing. Damage here causes selective face recognition deficits.

Now create a question about {category} following this exact format."""

    # Enhanced user prompt
    user_prompt = f"""Based on the following neuroscience information about {category}, create a Brain Bee question:

{relevant_content}

Generate a question that:
- Tests application of knowledge, not just recall
- Includes a realistic scenario or case study
- Has exactly 4 plausible options (A, B, C, D)
- Provides a detailed explanation that teaches the concept
- Is at Brain Bee competition level difficulty

Format your response EXACTLY as shown in the example above."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.6,  # Slightly lower for more consistency
        top_p=0.85,
        max_tokens=1000
    )
    
    return parse_and_validate_response(response.choices[0].message.content)

def parse_and_validate_response(response_text):
    """
    Robust parsing with validation and error handling.
    """
    try:
        # Use regex for more robust parsing
        import re
        
        # Extract components with regex
        question_match = re.search(r'Question:\s*(.+)', response_text, re.DOTALL)
        options_match = re.findall(r'Option ([A-D]):\s*(.+)', response_text)
        answer_match = re.search(r'Correct Answer:\s*([A-D])', response_text)
        explanation_match = re.search(r'Explanation:\s*(.+)', response_text, re.DOTALL)
        
        if not all([question_match, options_match, answer_match, explanation_match]):
            raise ValueError("Missing required components in response")
        
        if len(options_match) != 4:
            raise ValueError(f"Expected 4 options, found {len(options_match)}")
        
        # Validate answer is one of the options
        correct_answer = answer_match.group(1).upper()
        option_letters = [opt[0] for opt in options_match]
        if correct_answer not in option_letters:
            raise ValueError(f"Correct answer {correct_answer} not found in options {option_letters}")
        
        # Build choices list
        choices = []
        for letter, text in sorted(options_match):
            choices.append(f"Option {letter}: {text.strip()}")
        
        return {
            'question': question_match.group(1).strip(),
            'choices': choices,
            'correct_answer': correct_answer,
            'explanation': explanation_match.group(1).strip(),
            'quality_score': assess_question_quality(question_match.group(1), choices, explanation_match.group(1))
        }
        
    except Exception as e:
        # Fallback to original parsing if regex fails
        return fallback_parse(response_text)

def assess_question_quality(question, choices, explanation):
    """
    Assess the quality of the generated question.
    """
    quality_prompt = f"""Rate this neuroscience question on a scale of 1-10:

Question: {question}
Choices: {choices}
Explanation: {explanation}

Consider:
- Clarity and specificity
- Appropriate difficulty for Brain Bee
- Quality of distractors
- Educational value of explanation

Score: [1-10]
Reasoning: [brief explanation]"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a neuroscience education expert. Be strict and objective in your assessment."},
            {"role": "user", "content": quality_prompt}
        ],
        temperature=0.3
    )
    
    return response.choices[0].message.content

def create_semantic_chunks(text, max_chunk_size=8000):
    """
    Create semantic chunks instead of arbitrary truncation.
    """
    # Simple sentence-based chunking (could be improved with NLP)
    sentences = text.split('.')
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < max_chunk_size:
            current_chunk += sentence + "."
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + "."
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def select_most_relevant_chunks(chunks, category):
    """
    Select the most relevant chunks for the category.
    """
    # For now, return first few chunks
    # Could be improved with semantic similarity
    return "\n\n".join(chunks[:3]) 