import random

def get_random_supabase_question(supabase, category):
    """
    Fetch a random question from Supabase for the given category.
    Assumes a table 'questions' with columns: 'category', 'question', 'choices', 'correct_answer', 'explanation'.
    Returns (question, choices, correct_answer, explanation) or None if not found.
    """
    if not supabase:
        return None
    try:
        response = supabase.table('questions').select('*').eq('category', category).execute()
        data = response.data if hasattr(response, 'data') else response.get('data', [])
        if not data:
            return None
        q = random.choice(data)
        # Ensure choices is a list
        choices = q['choices']
        if isinstance(choices, str):
            import json
            choices = json.loads(choices)
        return q['question'], choices, q['correct_answer'], q.get('explanation', '')
    except Exception as e:
        print(f"Supabase fallback failed: {e}")
        return None
