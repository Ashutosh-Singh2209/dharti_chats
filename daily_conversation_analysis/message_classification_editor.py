# From /Users/ashutosh1/Documents/fyllo/dharti_chats
# streamlit run daily_conversation_analysis/message_classification_editor.py

import streamlit as st
import json
from pathlib import Path

# Page config
st.set_page_config(page_title="Message Classification Editor", layout="wide")

# Custom CSS for green message boxes
st.markdown("""
<style>
/* Style chat message containers */
div[data-testid="stChatMessage"] {
    background-color: #e8f5e9 !important;
    border: 2px solid #c8e6c9 !important;
    border-radius: 10px !important;
    padding: 15px !important;
    margin-bottom: 20px !important;
}

/* Force black text inside chat messages */
div[data-testid="stChatMessage"] * {
    color: #000000 !important;
}

/* EXCEPTION: Input fields should have white text to match dark theme background */
div[data-testid="stChatMessage"] textarea, 
div[data-testid="stChatMessage"] input {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    caret-color: #ffffff !important;
}

/* Remove default background if any and ensure avatars look good */
div[data-testid="stChatMessage"] .stChatMessageAvatar {
    background-color: transparent !important;
}

/* Fix buttons inside chat messages - Make text Blue */
div[data-testid="stChatMessage"] button {
    background-color: #ffffff !important;
    color: #1E88E5 !important;
    border-color: #1E88E5 !important;
}

/* Fix code blocks inside chat messages */
div[data-testid="stChatMessage"] code {
    color: #000000 !important;
    background-color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)

# Load conversations from JSON
def load_conversations(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_conversations(json_path, conversations):
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2, default=str)

def collect_user_messages(conversations, filter_common=True):
    """
    Collect all user messages with their context.
    
    Args:
        conversations: List of conversation objects
        filter_common: If True, only return common messages. If False, only uncommon (including unclassified).
    
    Returns:
        List of dicts with: conv_index, msg_index, conv_id, original, standalone, is_common
    """
    user_messages = []
    
    for conv_idx, conv in enumerate(conversations):
        conv_id = conv.get('_id', {})
        if isinstance(conv_id, dict):
            conv_id = conv_id.get('$oid', 'unknown')
        
        messages = conv.get('messages', [])
        
        for msg_idx, msg in enumerate(messages):
            role = msg.get('type') or msg.get('role')
            
            if role == 'user':
                is_common = msg.get('is_query_common')
                
                # For common view: only show messages explicitly tagged as common
                if filter_common:
                    if is_common is True:
                        user_messages.append({
                            'conv_index': conv_idx,
                            'msg_index': msg_idx,
                            'conv_id': conv_id,
                            'original': msg.get('content', 'N/A'),
                            'standalone': msg.get('standalone_question', 'N/A'),
                            'is_common': is_common
                        })
                # For uncommon view: show messages tagged as uncommon OR unclassified (missing/null)
                else:
                    if is_common is False or is_common is None or 'is_query_common' not in msg:
                        user_messages.append({
                            'conv_index': conv_idx,
                            'msg_index': msg_idx,
                            'conv_id': conv_id,
                            'original': msg.get('content', 'N/A'),
                            'standalone': msg.get('standalone_question', 'N/A'),
                            'is_common': is_common
                        })
    
    return user_messages

# Title
st.title("🏷️ Message Classification Editor")

# Select JSON file - Edit this path for different dates
json_dir = Path(__file__).parent / "30_Nov_2025"
json_path = json_dir / "conversations.json"

if not json_path.exists():
    st.error(f"No conversations.json found at: {json_path}")
    st.info("Edit line 107 in the code to change the date folder.")
    st.stop()

# Display current file
st.info(f"📁 Editing: `{json_path.parent.name}/conversations.json`")

# Load conversations
if 'conversations' not in st.session_state or st.session_state.get('last_file') != str(json_path):
    st.session_state.conversations = load_conversations(json_path)
    st.session_state.last_file = str(json_path)

conversations = st.session_state.conversations

# View mode selector
st.markdown("---")
view_mode = st.radio(
    "Select messages to view:",
    options=["Common Messages", "Uncommon Messages"],
    horizontal=True
)

filter_common = (view_mode == "Common Messages")

# Collect messages based on filter
user_messages = collect_user_messages(conversations, filter_common=filter_common)

st.markdown("---")
st.markdown(f"### Found {len(user_messages)} {view_mode}")

if len(user_messages) == 0:
    st.warning(f"No {view_mode.lower()} found in this file.")
    st.stop()

# Display messages
for idx, msg_data in enumerate(user_messages):
    with st.chat_message("user", avatar="👤"):
        st.markdown(f"#### Message {idx + 1} / {len(user_messages)}")
        
        # Display original message
        st.markdown(f"**📝 Original Message:**")
        st.markdown(f"{msg_data['original']}")
        
        st.markdown("---")
        
        # Display standalone question
        st.markdown(f"**🎯 Standalone Question:**")
        st.markdown(f"{msg_data['standalone']}")
        
        st.markdown("---")
        
        # Display conversation ID
        st.markdown(f"**🆔 Conversation ID:** `{msg_data['conv_id'][:12]}...`")
        
        st.markdown("---")
        
        # Action buttons
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            current_tag = "Common" if msg_data['is_common'] else "Uncommon"
            st.markdown(f"**Current Tag:** `{current_tag}`")
        
        with col2:
            # Button to tag as opposite
            if msg_data['is_common']:
                button_label = "Tag Uncommon"
                new_value = False
            else:
                button_label = "Tag Common"
                new_value = True
            
            if st.button(button_label, key=f"toggle_{idx}"):
                # Update the message in the original conversations list
                conv_idx = msg_data['conv_index']
                msg_idx = msg_data['msg_index']
                conversations[conv_idx]['messages'][msg_idx]['is_query_common'] = new_value
                
                # Save to file
                save_conversations(json_path, conversations)
                st.session_state.conversations = conversations
                
                st.success(f"✓ Tagged as {'Common' if new_value else 'Uncommon'}!")
                st.rerun()

st.markdown("---")
st.markdown(f"**Total Messages Displayed:** {len(user_messages)}")
