import random

def get_brain_bee_question_simple(category: str) -> str:
    """
    Intelligent content selection that picks random sections from the text file.
    This prevents the AI from always using the same content (like superior temporal gyrus).
    """
    filename = category + ".txt"
    
    # Load text
    with open(filename, 'r', encoding="utf-8") as file:
        information = file.read()
    
    # If file is small, use it all
    if len(information) <= 8000:
        return information
    
    # For larger files, select random sections to avoid bias
    sections = []
    section_size = 2000  # Each section is 2000 characters
    num_sections = 4     # We'll take 4 random sections
    
    # Split the text into sections
    total_sections = len(information) // section_size
    
    if total_sections <= num_sections:
        # If we have fewer sections than needed, use all
        return information[:8000]
    
    # Select random sections
    selected_indices = random.sample(range(total_sections), num_sections)
    
    for idx in selected_indices:
        start = idx * section_size
        end = start + section_size
        section = information[start:end]
        sections.append(section)
    
    # Combine sections
    relevant_content = " ".join(sections)
    
    # Ensure we don't exceed 8000 characters
    if len(relevant_content) > 8000:
        relevant_content = relevant_content[:8000]
    
    return relevant_content 