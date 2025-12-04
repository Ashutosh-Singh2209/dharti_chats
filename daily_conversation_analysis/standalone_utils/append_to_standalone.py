import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional


def check_if_similar_example_exists(user_input: str, existing_examples: str) -> bool:
    """
    Check if a similar example already exists in the few-shot examples.
    
    Args:
        user_input: The user input to check
        existing_examples: The existing few-shot examples string
        
    Returns:
        True if a similar example exists, False otherwise
    """
    # Split the examples by the separator
    examples = existing_examples.split("----------------------------------------")
    
    # Extract all "Follow Up Input:" entries
    for example in examples:
        if "Follow Up Input:" in example:
            lines = example.split("\n")
            for line in lines:
                if line.strip().startswith("Follow Up Input:"):
                    existing_input = line.replace("Follow Up Input:", "").strip()
                    # Simple exact match for now (can be enhanced with similarity)
                    if existing_input == user_input:
                        return True
    
    return False


def format_example(
    chat_history: List[Dict[str, str]], 
    user_input: str, 
    wrong_standalone: Optional[str], 
    correct_standalone: str,
    example_number: int
) -> str:
    """
    Format a new example in the same structure as existing examples.
    
    Args:
        chat_history: List of previous messages with 'role' and 'content'
        user_input: The current user input
        wrong_standalone: The wrong standalone question (can be None)
        correct_standalone: The correct standalone question
        example_number: The example number to use in the label
        
    Returns:
        Formatted example string
    """
    example_lines = []
    
    # Add example label
    example_lines.append(f"Example {example_number}:")
    
    # Add chat history if exists
    if chat_history:
        example_lines.append("Chat History:")
        for msg in chat_history:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            example_lines.append(f"{role}: {content}")
    else:
        example_lines.append("Chat History:")
        example_lines.append("None")
    
    # Add the follow-up input
    example_lines.append(f"Follow Up Input: {user_input}")
    
    # Add wrong standalone
    if wrong_standalone is None or wrong_standalone.strip() == "":
        example_lines.append("Wrong Standalone: None")
    else:
        example_lines.append(f"Wrong Standalone: {wrong_standalone}")
    
    # Add correct standalone
    example_lines.append(f"Correct Standalone Question: {correct_standalone}")
    
    # Don't add separator here - it's added by append_to_standalone_file
    
    return "\n".join(example_lines)


def get_next_example_number(existing_examples: str) -> int:
    """
    Determine the next example number by counting existing examples.
    
    Args:
        existing_examples: The existing few-shot examples string
        
    Returns:
        The next example number to use
    """
    import re
    # Find all "Example N:" patterns
    example_numbers = re.findall(r'Example (\d+):', existing_examples)
    if example_numbers:
        # Return the max number + 1
        return max(int(num) for num in example_numbers) + 1
    else:
        return 1


def append_to_standalone_file(example_text: str, file_path: str) -> None:
    """
    Append the formatted example to the standalone_query_examples.py file.
    
    Args:
        example_text: The formatted example text to append
        file_path: Path to the standalone_query_examples.py file
    """
    # Read the current file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the end of the few_shot_rephrase_examples string
    # It ends with "----------------------------------------\"\"\".strip()"
    
    # We need to insert the new example before the final closing
    # Find the pattern: ----------------------------------------""".strip()
    end_pattern = '----------------------------------------""".strip()'
    
    if end_pattern in content:
        # Split at the end pattern
        before_end = content.rsplit(end_pattern, 1)[0]
        
        # Remove all trailing separators and whitespace
        separator = "----------------------------------------"
        before_end = before_end.rstrip()
        while before_end.endswith(separator):
            before_end = before_end[:-len(separator)].rstrip()
        
        # Add the new example with proper formatting
        # Format: [existing content]\n[separator]\n[new example]\n[end_pattern]
        new_content = before_end + '\n' + separator + '\n' + example_text + '\n' + end_pattern
        
        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
    else:
        raise ValueError(f"Could not find the end pattern in {file_path}")


def process_and_append_message(
    conversation: Dict[str, Any], 
    message_index: int, 
    json_file_path: str
) -> Dict[str, Any]:
    """
    Main function to process a message and append it to standalone examples.
    
    Args:
        conversation: The full conversation object
        message_index: Index of the user message to process
        json_file_path: Path to the conversations JSON file
        
    Returns:
        Dictionary with 'status' (success/error) and 'message'
    """
    try:
        # Get the messages array
        messages = conversation.get('messages', [])
        
        if message_index >= len(messages):
            return {
                'status': 'error',
                'message': f'Invalid message index: {message_index}'
            }
        
        # Get the user message
        user_msg = messages[message_index]
        
        if user_msg.get('role') != 'user':
            return {
                'status': 'error',
                'message': 'Selected message is not a user message'
            }
        
        # Check if already added
        if user_msg.get('added_to_standalone_examples', False):
            return {
                'status': 'error',
                'message': 'This message has already been added to standalone examples'
            }
        
        # Get the correct translation
        correct_translation = user_msg.get('correct_translation', '').strip()
        
        if not correct_translation:
            return {
                'status': 'error',
                'message': 'No correct_translation found for this message. Please add it first.'
            }
        
        # Get the user input (content)
        user_input = user_msg.get('content', '').strip()
        
        if not user_input:
            return {
                'status': 'error',
                'message': 'User message has no content'
            }
        
        # Get wrong standalone (existing standalone_question or None)
        wrong_standalone = user_msg.get('standalone_question')
        
        # Build chat history (all messages before this one)
        chat_history = []
        for i in range(message_index):
            msg = messages[i]
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            if content:
                chat_history.append({'role': role, 'content': content})
        
        # Path to standalone_query_examples.py
        standalone_file_path = Path(__file__).parent.parent.parent.parent / "new_pull" / "fyllo-ai" / "bot_core" / "standalone_query_examples.py"
        standalone_file_path = str(standalone_file_path.resolve())
        
        # Read existing examples
        with open(standalone_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract the few_shot_rephrase_examples string
        # Find the content between the triple quotes
        start_marker = 'few_shot_rephrase_examples = f"""'
        end_marker = '""".strip()'
        
        if start_marker in content and end_marker in content:
            start_idx = content.index(start_marker) + len(start_marker)
            end_idx = content.rindex(end_marker)
            existing_examples = content[start_idx:end_idx]
        else:
            return {
                'status': 'error',
                'message': 'Could not parse existing examples from standalone file'
            }
        
        # Check if similar example exists
        if check_if_similar_example_exists(user_input, existing_examples):
            return {
                'status': 'error',
                'message': 'A similar example with this user input already exists in standalone examples'
            }
        
        # Get the next example number
        next_example_num = get_next_example_number(existing_examples)
        
        # Format the new example
        example_text = format_example(chat_history, user_input, wrong_standalone, correct_translation, next_example_num)
        
        # Append to standalone file
        append_to_standalone_file(example_text, standalone_file_path)
        
        # Mark the message as added in the conversation
        user_msg['added_to_standalone_examples'] = True
        
        # Save the updated conversation JSON
        # Read all conversations
        with open(json_file_path, 'r', encoding='utf-8') as f:
            all_conversations = json.load(f)
        
        # Find and update the conversation
        conv_id = conversation.get('_id')
        for i, conv in enumerate(all_conversations):
            if conv.get('_id') == conv_id:
                all_conversations[i] = conversation
                break
        
        # Save back to file
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(all_conversations, f, ensure_ascii=False, indent=2)
        
        return {
            'status': 'success',
            'message': f'Successfully added example to standalone file and marked message as added!'
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Error: {str(e)}'
        }
