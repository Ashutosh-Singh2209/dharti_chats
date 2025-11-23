# From /Users/ashutosh1/Documents/fyllo/dharti_chats
# streamlit run daily_conversation_analysis/conversation_viewer.py

import streamlit as st
import json
from pathlib import Path
from datetime import datetime

# Page config
st.set_page_config(page_title="Conversation Viewer", layout="wide")


# Custom CSS for message boxes
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

/* Fix buttons inside chat messages - Make text Blue as requested */
div[data-testid="stChatMessage"] button {
    background-color: #ffffff !important;
    color: #1E88E5 !important;
    border-color: #1E88E5 !important;
}

/* Fix code blocks (like Current Tag display) inside chat messages */
div[data-testid="stChatMessage"] code {
    color: #000000 !important;
    background-color: #ffffff !important; /* Force white background for code blocks so black text is visible */
}
</style>
""", unsafe_allow_html=True)

# Load conversations from JSON
def load_conversations(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        st.session_state['conversations'] = data
        return data

def load_conversations_no_cache(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        st.session_state['conversations'] = data
        return data

def is_conversation_common(conv):
    """
    Check if a conversation is composed ENTIRELY of common messages.
    Returns True if ALL user messages have is_query_common=True.
    Returns False if ANY user message has is_query_common=False or key is missing.
    If there are no user messages, returns False (show it).
    """
    messages = conv.get('messages', [])
    user_messages = [m for m in messages if m.get('role') == 'user']
    
    if not user_messages:
        return False
        
    for msg in user_messages:
        # If any message is NOT common (False or missing/None), the conversation is NOT fully common
        if msg.get('is_query_common') is not True:
            return False
            
    # If we get here, all user messages are common
    return True

def save_conversations(json_path, conversations):
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)
    # Update session state immediately after save
    st.session_state['conversations'] = conversations
    filtered_conversations = [c for c in conversations if not is_conversation_common(c)]
    st.session_state['filtered_conversations'] = filtered_conversations

# File selector
st.title("📊 Conversation Viewer & Annotator")

# Select JSON file
json_dir = Path(__file__).parent / "19_Nov_2025"
json_files = [json_dir / "conversations.json"]

if not json_files or not json_files[0].exists():
    st.error("No conversations.json files found!")
    st.stop()

selected_file = st.selectbox(
    "Select conversation file:",
    json_files,
    format_func=lambda x: f"{x.parent.name}/conversations.json"
)

# Load conversations
if 'conversations' not in st.session_state:
    conversations = load_conversations(selected_file)
else:
    conversations = st.session_state['conversations']

# Filter conversations
# We want to show conversations that are NOT fully common
if "filtered_conversations" not in st.session_state:
    filtered_conversations = [c for c in conversations if not is_conversation_common(c)]
    st.session_state['filtered_conversations'] = filtered_conversations
else:
    filtered_conversations = st.session_state['filtered_conversations']
total_conversations = len(filtered_conversations)

if total_conversations == 0:
    st.warning("No conversations to display (all filtered out as common).")
    st.stop()

# Initialize session state
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0

# Initialize global view settings if not present
if 'view_show_original' not in st.session_state:
    st.session_state.view_show_original = False
if 'view_show_translit' not in st.session_state:
    st.session_state.view_show_translit = False
if 'view_show_en' not in st.session_state:
    st.session_state.view_show_en = False
if 'view_show_pratibha' not in st.session_state:
    st.session_state.view_show_pratibha = False

def update_view_setting(setting_key, widget_key):
    """Update global setting based on widget state"""
    st.session_state[setting_key] = st.session_state[widget_key]

# Adjust index if out of bounds (can happen after filtering)
if st.session_state.current_index >= total_conversations:
    st.session_state.current_index = max(0, total_conversations - 1)

# Navigation
col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    if st.button("⬅️ Previous", disabled=st.session_state.current_index == 0):
        st.session_state.current_index -= 1
        st.rerun()
        
with col2:
    st.markdown(f"<h3 style='text-align: center;'>Conversation {st.session_state.current_index + 1} / {total_conversations}</h3>", unsafe_allow_html=True)
    
with col3:
    if st.button("Next ➡️", disabled=st.session_state.current_index >= total_conversations - 1):
        st.session_state.current_index += 1
        st.rerun()

# Current conversation (from filtered list)
conv = filtered_conversations[st.session_state.current_index]

# Status editor
st.markdown("---")
col_status1, col_status2 = st.columns([3, 1])

with col_status1:
    current_status = conv.get('status', 'None')
    st.markdown(f"**Status:** `{current_status}`")

with col_status2:
    new_status = st.text_input("Update status:", value=current_status, key=f"status_{st.session_state.current_index}")
    if st.button("💾 Save Status"):
        conv['status'] = new_status
        # Save the FULL list, not just filtered
        save_conversations(selected_file, conversations)
        st.success("Status saved!")
        st.rerun()

st.markdown("---")

# Metadata section (collapsible)
with st.expander("📋 Conversation Metadata", expanded=False):
    meta_col1, meta_col2 = st.columns(2)
    
    with meta_col1:
        st.markdown(f"**Conversation ID:** `{conv.get('_id', 'N/A')}`")
        st.markdown(f"**Farmer ID:** `{conv.get('farmer_id', 'N/A')}`")
        st.markdown(f"**Farmer Name:** `{conv.get('farmer_name', 'N/A')}`")
        st.markdown(f"**Gender:** `{conv.get('gender', 'N/A')}`")
    
    with meta_col2:
        st.markdown(f"**Language:** `{conv.get('language', 'N/A')}`")
        plot_ids = conv.get('farmer_plot_ids', [])
        st.markdown(f"**Plot IDs:** `{', '.join(plot_ids) if plot_ids else 'N/A'}`")
        
        expiry = conv.get('expiry', {})
        if '$date' in expiry:
            expiry_date = datetime.fromisoformat(expiry['$date'].replace('Z', '+00:00'))
            st.markdown(f"**Expiry:** `{expiry_date.strftime('%Y-%m-%d %H:%M:%S')}`")
        else:
            st.markdown(f"**Expiry:** `N/A`")

# Messages
st.markdown("### 💬 Messages")

messages = conv.get('messages', [])

for idx, msg in enumerate(messages):
    role = msg.get('role', 'unknown')
    
    if role == 'user':
        # User message
        with st.chat_message("user", avatar="👤"):
            st.markdown(f"#### User Message {idx // 2 + 1}")
            
            # Standalone question (always visible)
            standalone = msg.get('standalone_question', 'N/A')
            st.markdown(f"**🎯 Standalone Question:** {standalone}")
            
            st.markdown("---")
            
            # Toggleable fields
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                key_orig = f"orig_{st.session_state.current_index}_{idx}"
                st.checkbox("Show Original", value=st.session_state.view_show_original, key=key_orig, on_change=update_view_setting, args=('view_show_original', key_orig))
            with col2:
                key_translit = f"translit_{st.session_state.current_index}_{idx}"
                st.checkbox("Show Transliteration", value=st.session_state.view_show_translit, key=key_translit, on_change=update_view_setting, args=('view_show_translit', key_translit))
            with col3:
                key_en = f"en_user_{st.session_state.current_index}_{idx}"
                st.checkbox("Show English", value=st.session_state.view_show_en, key=key_en, on_change=update_view_setting, args=('view_show_en', key_en))
            with col4:
                key_pratibha = f"pratibha_toggle_{st.session_state.current_index}_{idx}"
                st.checkbox("Show Translation by Pratibha", value=st.session_state.view_show_pratibha, key=key_pratibha, on_change=update_view_setting, args=('view_show_pratibha', key_pratibha))
            
            if st.session_state.view_show_original:
                st.markdown(f"**Original:** {msg.get('content', 'N/A')}")
            
            if st.session_state.view_show_translit:
                st.markdown(f"**Transliteration:** {msg.get('content_transliterated', 'N/A')}")
            
            if st.session_state.view_show_en:
                st.markdown(f"**English:** {msg.get('en', 'N/A')}")
            
            # Pratibha field (editable)
            if st.session_state.view_show_pratibha:
                current_pratibha = msg.get('pratibha', '')
                pratibha_col1, pratibha_col2 = st.columns([4, 1])
                
                with pratibha_col1:
                    new_pratibha = st.text_area(
                        f"Pratibha Translation:",
                        value=current_pratibha,
                        key=f"pratibha_input_{st.session_state.current_index}_{idx}",
                        height=100
                    )
                
                with pratibha_col2:
                    if st.button("💾 Save", key=f"pratibha_save_{st.session_state.current_index}_{idx}"):
                        msg['pratibha'] = new_pratibha
                        save_conversations(selected_file, conversations)
                        st.success("Saved!")
                        conversations = load_conversations_no_cache(selected_file)
                        st.rerun()
            
            # Common Query Tagging
            st.markdown("---")
            st.markdown("##### 🏷️ Common Query Tagging")
            
            is_common = msg.get('is_query_common')
            tag_display = "None"
            if is_common is True:
                tag_display = "Common"
            elif is_common is False:
                tag_display = "Un-common"
                
            col_common1, col_common2, col_common3 = st.columns([2, 1, 1])
            
            with col_common1:
                st.markdown(f"**Current Tag:** `{tag_display}`")
                
            with col_common2:
                if st.button("Tag Common", key=f"tag_common_{st.session_state.current_index}_{idx}"):
                    msg['is_query_common'] = True
                    save_conversations(selected_file, conversations)
                    st.rerun()
                    
            with col_common3:
                if st.button("Tag Un-common", key=f"tag_uncommon_{st.session_state.current_index}_{idx}"):
                    msg['is_query_common'] = False
                    save_conversations(selected_file, conversations)
                    st.rerun()

            # Timestamp
            timestamp = msg.get('timestamp', {})
            if '$date' in timestamp:
                ts = datetime.fromisoformat(timestamp['$date'].replace('Z', '+00:00'))
                st.caption(f"🕒 {ts.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            st.markdown("---")
    
    elif role == 'assistant':
        # Assistant message (only English)
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(f"#### Assistant Message {idx // 2 + 1}")
            
            english_content = msg.get('en', 'N/A')
            st.markdown(english_content)
            
            # Timestamp
            timestamp = msg.get('timestamp', {})
            if '$date' in timestamp:
                ts = datetime.fromisoformat(timestamp['$date'].replace('Z', '+00:00'))
                st.caption(f"🕒 {ts.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        # Get the corresponding user message (should be the previous message)
        if idx > 0 and messages[idx - 1].get('role') == 'user':
            user_msg = messages[idx - 1]
            
            st.markdown("---")
            st.markdown("##### 📝 Review & Instructions")
                
            # Response correctness check (always visible)
            response_correct_col1, response_correct_col2 = st.columns([3, 1])
            
            with response_correct_col1:
                current_response_correct = user_msg.get('is_response_by_dharti_correct', 'N/A')
                st.markdown(f"**Is Dharti's response correct?** `{current_response_correct}`")
            
            with response_correct_col2:
                new_response_correct = st.selectbox(
                    "Select:",
                    options=['N/A', 'yes', 'no'],
                    index=['N/A', 'yes', 'no'].index(current_response_correct) if current_response_correct in ['N/A', 'yes', 'no'] else 0,
                    key=f"response_correct_{st.session_state.current_index}_{idx}"
                )
                if st.button("💾", key=f"save_response_{st.session_state.current_index}_{idx}"):
                    user_msg['is_response_by_dharti_correct'] = new_response_correct
                    save_conversations(selected_file, conversations)
                    st.success("✓")
                    conversations = load_conversations_no_cache(selected_file)
                    st.rerun()
            
            # Instructions fields (toggleable)
            st.markdown("---")
            instr_col1, instr_col2 = st.columns(2)
            
            with instr_col1:
                show_my_instructions = st.checkbox("Show My Instructions", key=f"show_my_instr_{st.session_state.current_index}_{idx}")
            
            with instr_col2:
                show_ankit_instructions = st.checkbox("Show Ankit Sir's Instructions", key=f"show_ankit_instr_{st.session_state.current_index}_{idx}")
            
            # My instructions
            if show_my_instructions:
                current_my_instr = user_msg.get('instructions_by_me', '')
                my_instr_col1, my_instr_col2 = st.columns([4, 1])
                
                with my_instr_col1:
                    new_my_instr = st.text_area(
                        "My Instructions:",
                        value=current_my_instr,
                        key=f"my_instr_input_{st.session_state.current_index}_{idx}",
                        height=100
                    )
                
                with my_instr_col2:
                    if st.button("💾", key=f"my_instr_save_{st.session_state.current_index}_{idx}"):
                        user_msg['instructions_by_me'] = new_my_instr
                        save_conversations(selected_file, conversations)
                        st.success("✓")
                        conversations = load_conversations_no_cache(selected_file)
                        st.rerun()
            
            # Ankit's instructions
            if show_ankit_instructions:
                current_ankit_instr = user_msg.get('instructions_by_ankit_sir', '')
                ankit_instr_col1, ankit_instr_col2 = st.columns([4, 1])
                
                with ankit_instr_col1:
                    new_ankit_instr = st.text_area(
                        "Ankit Sir's Instructions:",
                        value=current_ankit_instr,
                        key=f"ankit_instr_input_{st.session_state.current_index}_{idx}",
                        height=100
                    )
                
                with ankit_instr_col2:
                    if st.button("💾", key=f"ankit_instr_save_{st.session_state.current_index}_{idx}"):
                        user_msg['instructions_by_ankit_sir'] = new_ankit_instr
                        save_conversations(selected_file, conversations)
                        st.success("✓")
                        conversations = load_conversations_no_cache(selected_file)
                        st.rerun()
            
            st.markdown("---")

# Bottom section: Tags and Sentiment
st.markdown("### 🏷️ Tags & Sentiment")

col_tag1, col_tag2 = st.columns(2)

with col_tag1:
    tags = conv.get('tags', [])
    if tags:
        tag_str = ", ".join([f"`{tag}`" for tag in tags])
        st.markdown(f"**Tags:** {tag_str}")
    else:
        st.markdown("**Tags:** None")

with col_tag2:
    sentiment = conv.get('sentiment', 'N/A')
    st.markdown(f"**Sentiment:** `{sentiment}`")
