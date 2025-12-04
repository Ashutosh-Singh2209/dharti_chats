# streamlit run daily_conversation_analysis/conversation_viewer.py

import streamlit as st
import json
from pathlib import Path
from datetime import datetime
from standalone_utils import process_and_append_message

st.set_page_config(page_title="Conversation Viewer", layout="wide")

st.markdown("""
<style>
div[data-testid="stChatMessage"] {
    background-color: #e8f5e9 !important;
    border: 2px solid #1E88E5 !important;
    border-radius: 10px !important;
    padding: 15px !important;
    margin-bottom: 20px !important;
}
div[data-testid="stChatMessage"] * {
    color: #000000 !important;
}
div[data-testid="stChatMessage"] textarea, 
div[data-testid="stChatMessage"] input {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    caret-color: #ffffff !important;
}
div[data-testid="stChatMessage"] .stChatMessageAvatar {
    background-color: transparent !important;
}
div[data-testid="stChatMessage"] button {
    background-color: #ffffff !important;
    color: #1E88E5 !important;
    border-color: #1E88E5 !important;
}
div[data-testid="stChatMessage"] code {
    color: #000000 !important;
    background-color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)

def load_conversations(json_path):
    print(f"\nloading conversations for {json_path}\n")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        st.session_state['conversations'] = data
        return data

def is_conversation_common(conv):
    messages = conv.get('messages', [])
    user_messages = [m for m in messages if m.get('role') == 'user']
    if not user_messages:
        return False
    for msg in user_messages:
        if msg.get('is_query_common') is not True:
            return False
    return True

def save_conversations(json_path, conversations):
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)

json_dir = Path(__file__).parent / "19_Nov_2025"
json_files = [json_dir / "conversations.json"]
selected_json_file = json_files[0]

st.title(f"📊 Conversation Viewer & Annotator {json_files[0].parent.name}")

if not json_files or not json_files[0].exists():
    st.error("No conversations.json files found!")
    st.stop()

if 'conversations' not in st.session_state:
    conversations = load_conversations(selected_json_file)
    st.session_state['conversations'] = conversations
else:
    conversations = st.session_state['conversations']

if "filtered_conversation_ids" not in st.session_state:
    filtered_conversation_ids = [c['_id'] for c in conversations if not is_conversation_common(c)]
    st.session_state['filtered_conversation_ids'] = filtered_conversation_ids
else:
    filtered_conversation_ids = st.session_state['filtered_conversation_ids']

total_conversations = len(filtered_conversation_ids)

if total_conversations == 0:
    st.warning("No conversations to display.")
    st.stop()

if 'current_index' not in st.session_state:
    st.session_state.current_index = 0

if 'view_show_original' not in st.session_state:
    st.session_state.view_show_original = False
if 'view_show_translit' not in st.session_state:
    st.session_state.view_show_translit = False
if 'view_show_en' not in st.session_state:
    st.session_state.view_show_en = False
if 'view_show_correct_translation' not in st.session_state:
    st.session_state.view_show_correct_translation = False

def update_view_setting(setting_key, widget_key):
    st.session_state[setting_key] = st.session_state[widget_key]

if st.session_state.current_index >= total_conversations:
    st.session_state.current_index = max(0, total_conversations - 1)

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

def find_conversation_by_id(conversation_id):
    for conv in conversations:
        if conv['_id'] == conversation_id:
            return conv
    return None

conv = find_conversation_by_id(filtered_conversation_ids[st.session_state.current_index])

st.markdown("---")
col_status1, col_status2, col_status3, col_status4 = st.columns([1, 1, 1, 1])

with col_status1:
    current_status = conv.get('status', 'None')
    st.markdown(f"**Status:** `{current_status}`")

with col_status2:
    new_status = st.text_input("Update status:", value=current_status, key=f"status_{st.session_state.current_index}")
    if st.button("💾 Save Status"):
        conv['status'] = new_status
        save_conversations(selected_json_file, conversations)
        st.success("Status saved!")
        st.rerun()

with col_status1:
    current_status = conv.get('added_to_deep_eval_test', 'None')
    st.markdown(f"**Added to Deep_eval test:** `{current_status}`")

with col_status2:
    new_status = st.text_input("Deep_eval test status:", value=current_status, key=f"deep_eval_test_status_{st.session_state.current_index}")
    if st.button("💾 Save Deep_eval test status"):
        conv['added_to_deep_eval_test'] = new_status
        save_conversations(selected_json_file, conversations)
        st.success("Deep_eval test status saved!")
        st.rerun()

st.markdown("---")

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
        if isinstance(expiry, str):
            st.markdown(f"**Expiry:** `{expiry}`")
        elif isinstance(expiry, dict) and '$date' in expiry:
            expiry_date = datetime.fromisoformat(expiry['$date'].replace('Z', '+00:00'))
            st.markdown(f"**Expiry:** `{expiry_date.strftime('%Y-%m-%d %H:%M:%S')}`")
        else:
            st.markdown(f"**Expiry:** `N/A`")

st.markdown("### 💬 Messages")

messages = conv.get('messages', [])

for idx, msg in enumerate(messages):
    role = msg.get('role', 'unknown')

    if role == 'user':
        with st.chat_message("user", avatar="👤"):
            st.markdown(f"#### User Message {idx // 2 + 1}")
            timestamp = msg.get('timestamp', {})
            if isinstance(timestamp, str):
                try:
                    ts = datetime.fromisoformat(timestamp)
                    st.caption(f"🕒 {ts.strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    st.caption(f"🕒 {timestamp}")
            elif isinstance(timestamp, dict) and '$date' in timestamp:
                ts = datetime.fromisoformat(timestamp['$date'].replace('Z', '+00:00'))
                st.caption(f"🕒 {ts.strftime('%Y-%m-%d %H:%M:%S UTC')}")

            standalone = msg.get('standalone_question', 'N/A')
            st.markdown(f"**🎯 Standalone Question:** {standalone}")
            st.markdown("---")

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
                key_correct_translation = f"correct_translation_{st.session_state.current_index}_{idx}"
                st.checkbox("Show correct Translation", value=st.session_state.view_show_correct_translation, key=key_correct_translation, on_change=update_view_setting, args=('view_show_correct_translation', key_correct_translation))

            if st.session_state.view_show_original:
                st.markdown(f"**Original:** {msg.get('content', 'N/A')}")
            if st.session_state.view_show_translit:
                st.markdown(f"**Transliteration:** {msg.get('content_transliterated', 'N/A')}")
            if st.session_state.view_show_en:
                st.markdown(f"**English:** {msg.get('en', 'N/A')}")

            if st.session_state.view_show_correct_translation:
                current_correct_translation = msg.get('correct_translation', '')
                correct_translation_col1, correct_translation_col2 = st.columns([4, 1])
                with correct_translation_col1:
                    new_correct_translation = st.text_area(
                        f"Correct Translation:",
                        value=current_correct_translation,
                        key=f"correct_translation_input_{st.session_state.current_index}_{idx}",
                        height=100
                    )
                with correct_translation_col2:
                    if st.button("💾 Save", key=f"correct_translation_save_{st.session_state.current_index}_{idx}"):
                        msg['correct_translation'] = new_correct_translation
                        save_conversations(selected_json_file, conversations)
                        st.success("Saved!")
                        st.rerun()

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
                    save_conversations(selected_json_file, conversations)
                    st.rerun()
            with col_common3:
                if st.button("Tag Un-common", key=f"tag_uncommon_{st.session_state.current_index}_{idx}"):
                    msg['is_query_common'] = False
                    save_conversations(selected_json_file, conversations)
                    st.rerun()

            st.markdown("---")
            st.markdown("##### ➕ Add to Standalone Examples")
            
            # Check if already added
            already_added = msg.get('added_to_standalone_examples', False)
            has_correct_translation = bool(msg.get('correct_translation', '').strip())
            
            standalone_col1, standalone_col2 = st.columns([3, 1])
            with standalone_col1:
                if already_added:
                    st.success("✓ This message has been added to standalone examples")
                elif not has_correct_translation:
                    st.warning("⚠️ Please add correct_translation first before adding to standalone examples")
                else:
                    st.info("Ready to add to standalone examples")
            
            with standalone_col2:
                button_disabled = already_added or not has_correct_translation
                if st.button("➕ Add to Standalone", key=f"add_standalone_{st.session_state.current_index}_{idx}", disabled=button_disabled):
                    # Call the utility function
                    result = process_and_append_message(conv, idx, str(selected_json_file))
                    
                    if result['status'] == 'success':
                        st.success(result['message'])
                        # Reload conversations to reflect the change
                        st.session_state['conversations'] = load_conversations(selected_json_file)
                        st.rerun()
                    else:
                        st.error(result['message'])

            st.markdown("---")
            # st.markdown("🧪 Deep Eval Test Parameters")
            # with st.expander(":red[Click to expand]", expanded=False):
            #     if 'deep_eval_test_params' not in msg:
            #         msg['deep_eval_test_params'] = {}
                
            #     deep_eval_params = msg['deep_eval_test_params']

            #     expected_tools = st.text_input(
            #         "Expected Tools:",
            #         value=deep_eval_params.get('expected_tools', ''),
            #         key=f"deep_eval_tools_{st.session_state.current_index}_{idx}"
            #     )
            #     expected_faq = st.text_input(
            #         "Expected FAQ:",
            #         value=deep_eval_params.get('expected_faq', ''),
            #         key=f"deep_eval_faq_{st.session_state.current_index}_{idx}"
            #     )
            #     correct_standalone = st.text_area(
            #         "Correct Standalone:",
            #         value=deep_eval_params.get('correct_standalone', ''),
            #         key=f"deep_eval_correct_standalone_{st.session_state.current_index}_{idx}",
            #         height=100
            #     )
            #     wrong_standalone = st.text_area(
            #         "Wrong Standalone:",
            #         value=deep_eval_params.get('wrong_standalone', ''),
            #         key=f"deep_eval_wrong_standalone_{st.session_state.current_index}_{idx}",
            #         height=100
            #     )
            #     expected_output = st.text_area(
            #         "Expected Output:",
            #         value=deep_eval_params.get('expected_output', ''),
            #         key=f"deep_eval_expected_output_{st.session_state.current_index}_{idx}",
            #         height=150
            #     )
                
            #     if st.button("💾 Save Deep-Eval-Test-Case", key=f"save_deep_eval_{st.session_state.current_index}_{idx}"):
            #         msg['deep_eval_test_params'] = {
            #             'expected_tools': expected_tools,
            #             'expected_faq': expected_faq,
            #             'correct_standalone': correct_standalone,
            #             'wrong_standalone': wrong_standalone,
            #             'expected_output': expected_output
            #         }
            #         save_conversations(selected_json_file, conversations)
            #         st.success("Deep Eval Test Case Saved!")
            #         st.rerun()

            # st.markdown("---")

    elif role == 'assistant':
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(f"#### Assistant Message {idx // 2 + 1}")
            english_content = msg.get('en', 'N/A')
            st.markdown(english_content)
            timestamp = msg.get('timestamp', {})
            if '$date' in timestamp:
                ts = datetime.fromisoformat(timestamp['$date'].replace('Z', '+00:00'))
                st.caption(f"🕒 {ts.strftime('%Y-%m-%d %H:%M:%S UTC')}")

        if idx > 0 and messages[idx - 1].get('role') == 'user':
            user_msg = messages[idx - 1]

            st.markdown("---")
            st.markdown("##### 📝 Review & Instructions")

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
                    save_conversations(selected_json_file, conversations)
                    st.success("✓")
                    st.rerun()

            st.markdown("---")
            instr_col1, instr_col2 = st.columns(2)
            with instr_col1:
                show_my_instructions = st.checkbox("Show My Instructions", key=f"show_my_instr_{st.session_state.current_index}_{idx}")
            with instr_col2:
                show_ankit_instructions = st.checkbox("Show Ankit Sir's Instructions", key=f"show_ankit_instr_{st.session_state.current_index}_{idx}")

            if show_my_instructions:
                current_my_instr = user_msg.get('instructions_by_me', '')
                my_instr_col1, my_instr_col2 = st.columns([4, 1])
                with my_instr_col1:
                    new_my_instr = st.text_area(
                        "My Instructions:",
                        value=current_my_instr,
                        key=f"my_instr_input_{st.session_state.current_index}_{idx}",
                        height=200
                    )
                with my_instr_col2:
                    if st.button("💾", key=f"my_instr_save_{st.session_state.current_index}_{idx}"):
                        user_msg['instructions_by_me'] = new_my_instr
                        save_conversations(selected_json_file, conversations)
                        st.success("✓")
                        st.rerun()

            if show_ankit_instructions:
                current_ankit_instr = user_msg.get('instructions_by_ankit_sir', '')
                ankit_instr_col1, ankit_instr_col2 = st.columns([4, 1])
                with ankit_instr_col1:
                    new_ankit_instr = st.text_area(
                        "Ankit Sir's Instructions:",
                        value=current_ankit_instr,
                        key=f"ankit_instr_input_{st.session_state.current_index}_{idx}",
                        height=200
                    )
                with ankit_instr_col2:
                    if st.button("💾", key=f"ankit_instr_save_{st.session_state.current_index}_{idx}"):
                        user_msg['instructions_by_ankit_sir'] = new_ankit_instr
                        save_conversations(selected_json_file, conversations)
                        st.success("✓")
                        st.rerun()

            st.markdown("---")

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
