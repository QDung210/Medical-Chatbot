import streamlit as st
import requests
import json
import uuid

st.set_page_config(
    page_title="Medical Chatbot",
    page_icon="🏥",
    layout="wide"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize session_id for PostgreSQL memory
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# App header
st.title("🏥 Medical Chatbot với PostgreSQL Memory")
st.write("Trợ lý AI chuyên ngành y tế - Lưu trữ lịch sử cuộc trò chuyện trong PostgreSQL!")

# Chat interface
with st.container():
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                st.write(message["content"])
                if "sources" in message and message["sources"]:
                    with st.expander("📚 Nguồn tham khảo"):
                        for i, source in enumerate(message["sources"], 1):
                            st.write(f"**{i}. {source['title']}**")
                            if source.get('url'):
                                st.write(f"🔗 [Link]({source['url']})")
                            st.write(f"📊 Độ liên quan: {source['score']:.2f}")
                            st.write("---")
            else:
                st.write(message["content"])

# Chat input
if prompt := st.chat_input("Hỏi tôi về vấn đề sức khỏe..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.write(prompt)

    # Get AI response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        sources = []
        
        try:
            # Call API with session_id for PostgreSQL memory
            response = requests.post(
                "http://localhost:8000/chat",
                json={
                    "message": prompt,
                    "session_id": st.session_state.session_id
                },
                stream=True,
                timeout=30
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data = line[6:]  # Remove 'data: '
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
                
                # Final display
                message_placeholder.write(full_response)
                
                # Show sources
                if sources:
                    with st.expander("📚 Nguồn tham khảo"):
                        for i, source in enumerate(sources, 1):
                            st.write(f"**{i}. {source['title']}**")
                            if source.get('url'):
                                st.write(f"🔗 [Link]({source['url']})")
                            st.write(f"📊 Độ liên quan: {source['score']:.2f}")
                            st.write("---")
            else:
                st.error(f"Lỗi API: {response.status_code}")
                full_response = "Xin lỗi, có lỗi xảy ra khi kết nối với server."
                
        except Exception as e:
            st.error(f"Lỗi: {str(e)}")
            full_response = "Xin lỗi, có lỗi xảy ra. Vui lòng thử lại."
    
    # Add assistant response to chat history
    st.session_state.messages.append({
        "role": "assistant", 
        "content": full_response,
        "sources": sources
    })

# Sidebar with info and controls
with st.sidebar:
    st.header("ℹ️ Thông tin")
    st.write("🔸 Chatbot y tế sử dụng AI")
    st.write("🔸 PostgreSQL Memory - Lưu trữ vĩnh viễn")
    st.write("🔸 Dựa trên kiến thức y học")
    st.write("🔸 Chỉ mang tính chất tham khảo")
    
    st.warning("⚠️ **Lưu ý**: Thông tin từ AI chỉ mang tính chất tham khảo. Hãy tham khảo ý kiến bác sĩ chuyên khoa!")
    
    # Clear conversation buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Xóa UI"):
            st.session_state.messages = []
            st.rerun()
    
    with col2:
        if st.button("🧠 Xóa PostgreSQL"):
            try:
                # Clear PostgreSQL memory
                requests.delete(f"http://localhost:8000/chat/{st.session_state.session_id}")
                # Clear UI and create new session
                st.session_state.messages = []
                st.session_state.session_id = str(uuid.uuid4())
                st.success("Đã xóa memory PostgreSQL!")
                st.rerun()
            except:
                st.error("Lỗi khi xóa PostgreSQL memory")
    
    # Session info
    st.divider()
    st.write(f"**Session ID**: `{st.session_state.session_id[:8]}...`")
    st.write(f"**Số tin nhắn UI**: {len(st.session_state.messages)}")
    
    # Memory approach info
    st.divider()
    st.success("🐘 **PostgreSQL Memory**: Lịch sử cuộc trò chuyện được lưu vào database PostgreSQL, có thể truy xuất lại sau khi restart!")
    
    # Database info
    st.info("📊 **Database**: localhost:5433/chatbot_db")