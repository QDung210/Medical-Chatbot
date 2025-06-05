import streamlit as st 
import requests 

st.set_page_config(page_title="Chatbot Y Tế", layout="wide")
st.title("Chatbot Y Tế")    

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Display chat history
st.subheader("Lịch sử chat")
for message in st.session_state.messages:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

# User input
prompt = st.chat_input("Vui lòng nhập câu hỏi...")

if prompt:
    # Add user message to chat history
    st.session_state.messages.append({"role": "Người dùng", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Call the API
    with st.spinner("Thinking ... 💭"):
        response = requests.post(
            url="http://localhost:8000/api/chat",  # Changed from rag-pipeline to localhost
            json={"messages": prompt}
        )
    
    if response.status_code == 200:
        answer = response.json().get("answer", "Không có câu trả lời.")
    else:
        answer = "Lỗi khi gọi API."

    # Add bot response to chat history
    st.session_state.messages.append({"role": "Trợ lý y tế", "content": answer})
    
    # Display bot response
    with st.chat_message("Trợ lý y tế"):
        st.markdown(answer)
