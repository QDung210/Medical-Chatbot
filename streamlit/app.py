import streamlit as st
import requests
import time

# Auto-detect API port
def find_api_port():
    """Find the running API port"""
    for port in range(8000, 8011):
        try:
            response = requests.get(f"http://127.0.0.1:{port}/health", timeout=2)
            if response.status_code == 200:
                return port
        except:
            continue
    return 8000  # Default fallback

API_PORT = find_api_port()
API_BASE_URL = f"http://127.0.0.1:{API_PORT}"

st.set_page_config(page_title="🏥 Trợ lý Y tế AI", page_icon="🏥", layout="wide")

st.markdown("""
<style>
.main-header { font-size: 2.5rem; color: #1f77b4; text-align: center; margin-bottom: 2rem; }
.chat-message { padding: 1rem; border-radius: 0.5rem; margin: 1rem 0; }
.user-message { background-color: #f0f2f6; border-left: 4px solid #1f77b4; }
.bot-message { background-color: #e8f4fd; border-left: 4px solid #28a745; }
.api-status { padding: 0.5rem; border-radius: 0.3rem; margin: 0.5rem 0; }
.status-connected { background-color: #d4edda; color: #155724; }
.status-disconnected { background-color: #f8d7da; color: #721c24; }
</style>
""", unsafe_allow_html=True)

def api_call(endpoint, method="GET", data=None):
    try:
        url = f"{API_BASE_URL}{endpoint}"
        response = requests.get(url, timeout=10) if method == "GET" else requests.post(url, json=data, timeout=30)
        return {"status": "success", "data": response.json()} if response.status_code == 200 else {"status": "error", "message": response.json().get("detail", "Lỗi API")}
    except requests.exceptions.ConnectionError:
        return {"status": "disconnected", "message": "Không thể kết nối API"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def display_sources(sources):
    # Chỉ hiển thị sources có điểm >= 0.7
    high_quality_sources = [s for s in sources if s.get('score', 0) >= 0.6]
    
    if not high_quality_sources:
        return
    
    st.markdown("**📚 Nguồn tham khảo:**")
    
    for i, source in enumerate(high_quality_sources, 1):
        metadata = source.get('metadata', {})
        title = metadata.get('title', metadata.get('name', f'Tài liệu {i}'))
        url = metadata.get('url', metadata.get('source', ''))
        score = source.get('score', 0)
        
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"📄 [{title}]({url})" if url else f"📄 {title}")
        with col2:
            st.caption(f"Điểm: {score:.2f}")

# Session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = 'llama-3.3-70b-versatile'

st.markdown('<h1 class="main-header">🏥 Trợ lý Y tế AI</h1>', unsafe_allow_html=True)

# API status
api_connection = api_call("/health")
status_class = "status-connected" if api_connection["status"] == "success" else "status-disconnected"
status_text = "✅ API kết nối thành công" if api_connection["status"] == "success" else f"❌ {api_connection.get('message', 'Lỗi API')}<br>Chạy: <code>python -m rag_pipeline.src.main</code>"
st.markdown(f'<div class="api-status {status_class}">{status_text}</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("ℹ️ Thông tin hệ thống")
    
    if api_connection["status"] == "success":
        st.subheader("🤖 Chọn AI Model")
        models_data = api_call("/models")
        
        if models_data["status"] == "success":
            available_models = models_data["data"]["available_models"]
            model_desc = {'llama-3.3-70b-versatile': '🦙 LLaMA 3.3 70B (Tốt nhất)', 'llama-3.1-8b-instant': '⚡ LLaMA 3.1 8B (Nhanh)'}
            
            new_model = st.selectbox("Chọn model:", available_models, 
                index=available_models.index(st.session_state.selected_model) if st.session_state.selected_model in available_models else 0,
                format_func=lambda x: model_desc.get(x, x))
            
            if new_model != st.session_state.selected_model:
                with st.spinner(f'🔄 Đang chuyển sang {new_model}...'):
                    result = api_call("/change-model", "POST", {"model_name": new_model})
                    if result["status"] == "success":
                        st.session_state.selected_model = new_model
                        st.success(f'✅ Đã chuyển sang {new_model}!')
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f'❌ Lỗi: {result["message"]}')
    
    st.markdown("---")
    
    if api_connection["status"] == "success":
        stats_data = api_call("/stats")
        if stats_data["status"] == "success":
            stats = stats_data["data"]
            if stats.get('status') == 'active':
                st.success("🟢 Đang hoạt động")
                st.metric("☁️ Vector Store", stats.get('vector_store', 'Unknown'))
                st.metric("📊 Tài liệu y tế", f"{stats.get('vector_count', 0):,}")
                st.metric("🤖 AI Model", stats.get('llm_model', 'Unknown'))
                embedding = stats.get('embedding_model', '').split('/')[-1] if stats.get('embedding_model') else 'Unknown'
                st.metric("🔍 Embedding", embedding)
            else:
                st.error(f"🔴 Lỗi: {stats.get('message', 'Unknown error')}")
    else:
        st.error("🔴 Chưa kết nối API")
    
    st.markdown("""
    ---
    ### 📋 Hướng dẫn
    1. Khởi động API: `python -m rag_pipeline.src.main`
    2. Đặt câu hỏi về sức khỏe
    3. Nhận tư vấn từ AI
    
    ### ⚠️ Lưu ý
    - Chỉ mang tính tham khảo
    - Tham khảo bác sĩ cho vấn đề nghiêm trọng
    """)
    
    if st.button("🗑️ Xóa lịch sử"):
        st.session_state.messages = []
        st.rerun()

# Chat
st.markdown("### 💬 Trò chuyện với trợ lý y tế")

for message in st.session_state.messages:
    role_class = "user-message" if message["role"] == "user" else "bot-message"
    role_icon = "👤 Bạn" if message["role"] == "user" else "🤖 Trợ lý Y tế"
    st.markdown(f'<div class="chat-message {role_class}"><strong>{role_icon}:</strong><br>{message["content"]}</div>', unsafe_allow_html=True)
    if message["role"] == "assistant" and "sources" in message:
        display_sources(message["sources"])

if prompt := st.chat_input("Đặt câu hỏi về sức khỏe..."):
    if api_connection["status"] != "success":
        st.error("❌ Vui lòng khởi động API trước!")
        st.stop()
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.markdown(f'<div class="chat-message user-message"><strong>👤 Bạn:</strong><br>{prompt}</div>', unsafe_allow_html=True)
    
    with st.spinner('🔍 Đang tìm kiếm thông tin...'):
        result = api_call("/query", "POST", {"question": prompt, "max_tokens": 1024})
        
        if result["status"] == "success":
            data = result["data"]
            answer = data.get("answer", "Không có phản hồi")
            sources = data.get("sources", [])
            
            st.markdown(f'<div class="chat-message bot-message"><strong>🤖 Trợ lý Y tế:</strong><br>{answer}</div>', unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
            display_sources(sources)
        else:
            st.error(f"❌ Lỗi: {result['message']}")

st.markdown("""
---
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    🏥 Trợ lý Y tế AI | Made with ❤️ for Healthcare<br>
    <small>Frontend: Streamlit | Backend: FastAPI + RAG</small>
</div>
""", unsafe_allow_html=True) 