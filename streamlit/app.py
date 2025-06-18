import streamlit as st
import requests
import json
import uuid

st.set_page_config(
    page_title="Medical Chatbot",
    page_icon="🏥",
    layout="wide"
)

# Add custom CSS for loading spinner
st.markdown("""
<style>
.loading-spinner {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 16px;
    color: #1f77b4;
}

.spinner {
    width: 20px;
    height: 20px;
    border: 2px solid #f3f3f3;
    border-top: 2px solid #1f77b4;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

.thinking-dots {
    animation: thinking 1.5s infinite;
}

@keyframes thinking {
    0%, 20% { opacity: 0.2; }
    50% { opacity: 1; }
    100% { opacity: 0.2; }
}
</style>
""", unsafe_allow_html=True)
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False
st.title("🏥 Medical Chatbot")
st.write("Trợ lý AI chuyên ngành y tế!")

with st.container():
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                st.write(message["content"])
                if "sources" in message and message["sources"]:
                    valid_sources = message["sources"]  
                    if valid_sources:
                        st.write("---")
                        st.write("📚 **Nguồn tham khảo:**")
                        for i, source in enumerate(valid_sources, 1):
                            score = source.get('score', 0)
                            if source.get('url'):
                                st.write(f"**{i}. [{source['title']}]({source['url']})** ")
                            else:
                                st.write(f"**{i}. {source['title']}** ")
                    else:
                        st.write("---")
                        st.write("❓ **Chatbot không có đủ thông tin đáng tin cậy để trả lời câu hỏi này.**")
                elif "sources" not in message or not message["sources"]:
                    st.write("---")
                    st.write("❓ **Chatbot không có đủ thông tin đáng tin cậy để trả lời câu hỏi này.**")
            else:
                st.write(message["content"])

if prompt := st.chat_input("Hỏi tôi về vấn đề sức khỏe..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.is_processing = True
    st.rerun()
if st.session_state.is_processing:
    last_user_message = None
    for msg in reversed(st.session_state.messages):
        if msg["role"] == "user":
            last_user_message = msg["content"]
            break
    
    if last_user_message:
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            sources = []
            
            # Show animated thinking indicator with spinner
            thinking_placeholder = st.empty()
            
            try:
                # Show beautiful spinner
                thinking_placeholder.markdown("""
                <div class="loading-spinner">
                    <div class="spinner"></div>
                    <span class="thinking-dots">🤔 Đang suy nghĩ và tìm kiếm thông tin y tế...</span>
                </div>
                """, unsafe_allow_html=True)
                
                response = requests.post(
                    "http://medical-fastapi:8000/chat",
                    json={
                        "message": last_user_message,
                        "session_id": st.session_state.session_id
                    },
                    stream=True,
                    timeout=60  
                )
                
                if response.status_code == 200:
                    # Clear thinking message and start showing response
                    thinking_placeholder.empty()
                    for line in response.iter_lines():
                        if line:
                            line = line.decode('utf-8')
                            if line.startswith('data: '):
                                data = line[6:]
                                if data == '[DONE]':
                                    break
                                try:
                                    chunk = json.loads(data)
                                    if chunk.get('type') == 'content':
                                        full_response += chunk.get('content', '')
                                        message_placeholder.write(full_response + "▌")
                                    elif chunk.get('type') == 'sources':
                                        sources = chunk.get('sources', [])
                                except json.JSONDecodeError:
                                    continue
                    message_placeholder.write(full_response)
                    if full_response:
                        print(f"DEBUG: Response length: {len(full_response)} characters")
                        print(f"DEBUG: Response ends with: '{full_response[-50:]}'")
                    if sources:
                        valid_sources = sources 
                        
                        if valid_sources:
                            st.write("---")
                            st.write("📚 **Nguồn tham khảo:**")
                            for i, source in enumerate(valid_sources, 1):
                                score = source.get('score', 0)
                                if source.get('url'):
                                    st.write(f"**{i}. [{source['title']}]({source['url']})** (Score: {score:.4f})")
                                else:
                                    st.write(f"**{i}. {source['title']}** (Score: {score:.4f})")
                        else:
                            st.write("---")
                            st.write("❓ **Chatbot không có đủ thông tin đáng tin cậy để trả lời câu hỏi này.**")
                    else:
                        st.write("---")
                        st.write("❓ **Chatbot không có đủ thông tin đáng tin cậy để trả lời câu hỏi này.**")
                else:
                    st.error(f"Lỗi API: {response.status_code}")
                    full_response = "Xin lỗi, có lỗi xảy ra khi kết nối với server."
                    
            except Exception as e:
                st.error(f"Lỗi: {str(e)}")
                full_response = "Xin lỗi, có lỗi xảy ra. Vui lòng thử lại."
        st.session_state.messages.append({
            "role": "assistant", 
            "content": full_response,
            "sources": sources
        })
        st.session_state.is_processing = False
        st.rerun()