import streamlit as st
import sys
import os
import atexit
from dotenv import load_dotenv
import requests

# Thêm đường dẫn tới thư mục gốc của project
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from rag_pipeline.src import create_pipeline, DEFAULT_MODEL, DEFAULT_COLLECTION

# Đường dẫn tuyệt đối tới file .env trong rag_pipeline
abs_env_path = os.path.join(project_root, 'rag_pipeline', '.env')
if os.path.exists(abs_env_path):
    load_dotenv(abs_env_path)

print("GROQ_API_KEY:", os.getenv("GROQ_API_KEY"))

# Cleanup function for session end
def cleanup_session():
    """Cleanup resources when session ends"""
    if 'rag_pipeline' in st.session_state and st.session_state.rag_pipeline:
        try:
            st.session_state.rag_pipeline.cleanup()
        except:
            pass

# Register cleanup
atexit.register(cleanup_session)

# Page config
st.set_page_config(
    page_title="🏥 Trợ lý Y tế AI",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #f0f2f6;
        border-left: 4px solid #1f77b4;
    }
    .bot-message {
        background-color: #e8f4fd;
        border-left: 4px solid #28a745;
    }
    .source-info {
        font-size: 0.8rem;
        color: #666;
        margin-top: 0.5rem;
        padding: 0.5rem;
        background-color: #f8f9fa;
        border-radius: 0.3rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'selected_model' not in st.session_state:
    st.session_state.selected_model = 'llama-3.3-70b-versatile'

if 'rag_pipeline' not in st.session_state:
    with st.spinner('🔄 Đang khởi tạo hệ thống AI...'):
        try:
            # Create pipeline with Qdrant Cloud
            st.session_state.rag_pipeline = create_pipeline(
                collection_name='medical_data',
                model_name=st.session_state.selected_model
            )
            st.success('✅ Hệ thống AI đã sẵn sàng!')
        except Exception as e:
            st.error(f'❌ Lỗi khởi tạo: {str(e)}')
            st.error('Vui lòng kiểm tra QDRANT_CLOUD_URL và QDRANT_API_KEY trong file .env')
            st.session_state.rag_pipeline = None

# Main header
st.markdown('<h1 class="main-header">🏥 Trợ lý Y tế AI</h1>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("ℹ️ Thông tin hệ thống")
    
    # Model Selection
    st.subheader("🤖 Chọn AI Model")
    available_models = [
        'llama-3.3-70b-versatile',
        'llama-3.1-8b-instant'
    ]
    
    model_descriptions = {
        'llama-3.3-70b-versatile': '🦙 LLaMA 3.3 70B (Tốt nhất)',
        'llama-3.1-8b-instant': '⚡ LLaMA 3.1 8B (Nhanh)'
    }
    
    new_model = st.selectbox(
        "Chọn model:",
        available_models,
        index=available_models.index(st.session_state.selected_model),
        format_func=lambda x: model_descriptions.get(x, x)
    )
    
    # Handle model change
    if new_model != st.session_state.selected_model:
        with st.spinner(f'🔄 Đang chuyển sang {new_model}...'):
            try:
                if st.session_state.rag_pipeline:
                    success = st.session_state.rag_pipeline.change_model(new_model)
                    if success:
                        st.session_state.selected_model = new_model
                        st.success(f'✅ Đã chuyển sang {new_model}!')
                        st.rerun()
                    else:
                        st.error('❌ Không thể chuyển model!')
                else:
                    # Create new pipeline with new model
                    st.session_state.rag_pipeline = create_pipeline(
                        collection_name='medical_data',
                        model_name=new_model
                    )
                    st.session_state.selected_model = new_model
                    st.success(f'✅ Đã khởi tạo {new_model}!')
                    st.rerun()
            except Exception as e:
                st.error(f'❌ Lỗi chuyển model: {str(e)}')
    
    st.markdown("---")
    
    if st.session_state.rag_pipeline:
        stats = st.session_state.rag_pipeline.get_stats()
        if stats['status'] == 'active':
            st.success("🟢 Đang hoạt động")
            st.metric("☁️ Kết nối", stats.get('connection_type', 'Unknown'))
            st.metric("📊 Tài liệu y tế", f"{stats['vector_count']:,}")
            st.metric("🤖 AI Model", stats['llm_model'])
            st.metric("🔍 Embedding", stats['embedding_model'].split('/')[-1])
        else:
            st.error("🔴 Lỗi hệ thống")
            # Show detailed error information
            st.error(f"Chi tiết lỗi: {stats}")
            if 'message' in stats:
                st.error(f"Thông báo: {stats['message']}")
            
            # Show available collections if any
            if 'available_collections' in stats:
                st.warning(f"Collections có sẵn: {', '.join(stats['available_collections'])}")
    else:
        st.error("🔴 Chưa kết nối")
    
    st.markdown("---")
    st.markdown("""
    ### 📋 Hướng dẫn sử dụng
    1. Đặt câu hỏi về sức khỏe
    2. Hệ thống sẽ tìm kiếm trong database y tế
    3. AI sẽ trả lời dựa trên thông tin chuyên môn
    
    ### ⚠️ Lưu ý
    - Thông tin chỉ mang tính tham khảo
    - Không thay thế tư vấn y tế chuyên nghiệp
    - Luôn tham khảo bác sĩ cho vấn đề nghiêm trọng
    """)
    
    if st.button("🗑️ Xóa lịch sử chat"):
        st.session_state.messages = []
        st.rerun()

# Main chat interface
st.markdown("### 💬 Trò chuyện với trợ lý y tế")

# Display chat messages
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(f"""
        <div class="chat-message user-message">
            <strong>👤 Bạn:</strong><br>
            {message["content"]}
        </div>
        """, unsafe_allow_html=True)
    else:
        # Display bot message
        st.markdown(f"""
        <div class="chat-message bot-message">
            <strong>🤖 Trợ lý Y tế:</strong><br>
            {message["content"]}
        </div>
        """, unsafe_allow_html=True)
        
        # Display sources using Streamlit components
        if "sources" in message and message["sources"]:
            # Check if highest confidence score is >= 0.6
            max_score = max(source.get('score', 0) for source in message["sources"])
            if max_score >= 0.6:
                st.markdown("**📚 Nguồn tham khảo:**")
                sources = message["sources"]
                
                def dedup_sources(sources, min_score=0.7):
                    # Lọc trùng theo (title, url), giữ lại bản có score cao nhất và score >= min_score
                    unique = {}
                    for src in sources:
                        score = src.get('score', 0)
                        if score < min_score:
                            continue
                        metadata = src.get('metadata', {})
                        title = metadata.get('title', metadata.get('name', ''))
                        url = metadata.get('url', metadata.get('source', metadata.get('link', '')))
                        key = (title, url)
                        if key not in unique or score > unique[key].get('score', 0):
                            unique[key] = src
                    return list(unique.values())
                
                sources = dedup_sources(sources, min_score=0.7)
                for i, source in enumerate(sources, 1):
                    metadata = source.get('metadata', {})
                    score = source.get('score', 0)
                    url = metadata.get('url', metadata.get('source', metadata.get('link', '')))
                    title = metadata.get('title', metadata.get('name', f'Tài liệu {i}'))
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        if url:
                            st.markdown(f"📄 [{title}]({url})")
                        else:
                            st.markdown(f"📄 {title}")
                            content_preview = source.get('content', '')[:100] + "..." if len(source.get('content', '')) > 100 else source.get('content', '')
                            st.caption(content_preview)
                    
                    with col2:
                        st.caption(f"Độ liên quan: {score:.2f}")
                    
                    if i < len(sources):
                        st.divider()

# Chat input
if prompt := st.chat_input("Đặt câu hỏi về sức khỏe của bạn..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message immediately
    st.markdown(f"""
    <div class="chat-message user-message">
        <strong>👤 Bạn:</strong><br>
        {prompt}
    </div>
    """, unsafe_allow_html=True)
    
    # Generate response
    if st.session_state.rag_pipeline:
        with st.spinner('🔍 Đang tìm kiếm thông tin y tế...'):
            try:
                # Get streaming response
                result = st.session_state.rag_pipeline.query(prompt, stream=True)
                
                # Display bot message header
                st.markdown("""
                <div class="chat-message bot-message">
                    <strong>🤖 Trợ lý Y tế:</strong><br>
                """, unsafe_allow_html=True)
                
                # Create placeholder for streaming text
                response_placeholder = st.empty()
                full_response = ""
                
                # Process streaming response
                if 'answer_stream' in result:
                    response_stream = result['answer_stream']
                    
                    # Parse SSE stream
                    for line in response_stream.iter_lines():
                        if line:
                            line = line.decode('utf-8')
                            if line.startswith('data: '):
                                data = line[6:]  # Remove 'data: ' prefix
                                if data == '[DONE]':
                                    break
                                try:
                                    import json
                                    chunk = json.loads(data)
                                    if chunk['choices'][0]['delta'].get('content'):
                                        delta = chunk['choices'][0]['delta']['content']
                                        full_response += delta
                                        response_placeholder.markdown(full_response)
                                except:
                                    continue
                else:
                    # Fallback to non-streaming
                    full_response = result.get('answer', 'Không có phản hồi')
                    response_placeholder.markdown(full_response)
                
                # Close the bot message div
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Add to session state
                bot_message = {
                    "role": "assistant", 
                    "content": full_response,
                    "sources": result["sources"]
                }
                st.session_state.messages.append(bot_message)
                
                # Display sources using Streamlit components
                if result["sources"]:
                    # Check if highest confidence score is >= 0.6
                    max_score = max(source.get('score', 0) for source in result["sources"])
                    if max_score >= 0.6:
                        st.markdown("**📚 Nguồn tham khảo:**")
                        sources = result["sources"]
                        
                        def dedup_sources(sources, min_score=0.7):
                            # Lọc trùng theo (title, url), giữ lại bản có score cao nhất và score >= min_score
                            unique = {}
                            for src in sources:
                                score = src.get('score', 0)
                                if score < min_score:
                                    continue
                                metadata = src.get('metadata', {})
                                title = metadata.get('title', metadata.get('name', ''))
                                url = metadata.get('url', metadata.get('source', metadata.get('link', '')))
                                key = (title, url)
                                if key not in unique or score > unique[key].get('score', 0):
                                    unique[key] = src
                            return list(unique.values())
                        
                        sources = dedup_sources(sources, min_score=0.7)
                        for i, source in enumerate(sources, 1):
                            metadata = source.get('metadata', {})
                            score = source.get('score', 0)
                            url = metadata.get('url', metadata.get('source', metadata.get('link', '')))
                            title = metadata.get('title', metadata.get('name', f'Tài liệu {i}'))
                            col1, col2 = st.columns([4, 1])
                            with col1:
                                if url:
                                    st.markdown(f"📄 [{title}]({url})")
                                else:
                                    st.markdown(f"📄 {title}")
                                    content_preview = source.get('content', '')[:100] + "..." if len(source.get('content', '')) > 100 else source.get('content', '')
                                    st.caption(content_preview)
                            
                            with col2:
                                st.caption(f"Độ liên quan: {score:.2f}")
                            
                            if i < len(sources):
                                st.divider()
                
            except Exception as e:
                st.error(f"❌ Lỗi xử lý: {str(e)}")
    else:
        st.error("❌ Hệ thống chưa sẵn sàng. Vui lòng làm mới trang.")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    🏥 Trợ lý Y tế AI | Tác giả Đỗ Quốc Dũng| Made with ❤️ for Healthcare
</div>
""", unsafe_allow_html=True)

# Test Groq API
api_key = os.getenv("GROQ_API_KEY")
print("GROQ_API_KEY:", api_key)
response = requests.get(
    'https://api.groq.com/openai/v1/models',
    headers={'Authorization': f'Bearer {api_key}'},
    timeout=10
)
print("Status code:", response.status_code)
print("Response:", response.text) 