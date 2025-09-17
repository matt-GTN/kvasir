import json

def remove_json_blocks(text):
    """
    Simple version that removes common JSON code block patterns.
    
    Args:
        text (str or dict): The input string containing JSON code blocks
        
    Returns:
        str: The cleaned string with code block markers removed.
    """
    text = text.replace('```json', '').replace('```', '')
    return text.strip()
