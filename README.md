# 🏥 Medical Chatbot with RAG Pipeline

Chatbot y tế thông minh sử dụng RAG (Retrieval-Augmented Generation) với 346,968 tài liệu y tế từ Việt Nam.

## ✨ Tính năng

- 💬 Chat với AI về các vấn đề y tế
- 🔍 Tìm kiếm thông tin từ 346,968 tài liệu y tế
- 📚 Hiển thị nguồn tham khảo đáng tin cậy
- 🚀 Streaming responses (trả lời realtime)
- 🐳 Docker containerized (dễ deploy)

## 🛠️ Công nghệ sử dụng

- **Frontend**: Streamlit
- **Backend**: FastAPI
- **Vector Database**: Qdrant
- **SQL Database**: PostgreSQL
- **LLM**: Groq (Llama 3.1 8B)
- **Embeddings**: M3-retriever-MEDICAL

## 📋 Yêu cầu hệ thống

- Docker & Docker Compose
- Groq API key (miễn phí tại [groq.com](https://groq.com))
- Ít nhất 4GB RAM
- 5GB dung lượng ổ cứng

## 🚀 Hướng dẫn cài đặt

### Bước 1: Clone repository

```bash
git clone <repository-url>
cd Medical_chatbot_by_self
```

### Bước 2: Tạo Groq API key

1. Truy cập [console.groq.com](https://console.groq.com)
2. Đăng ký/đăng nhập tài khoản
3. Tạo API key mới
4. Copy API key

### Bước 3: Cấu hình environment

```bash
# Copy file example và đổi tên
cp example.env .env

# Sửa file .env với API key của bạn
GROQ_API_KEY=your_groq_api_key_here
QDRANT_URL=http://qdrant:6333
DEFAULT_MODEL=llama-3.1-8b-instant
```

### Bước 4: Chuẩn bị dữ liệu vector

**Option A: Sử dụng snapshot có sẵn (khuyến nghị)**
1. Download file `medical_data.snapshot` (liên hệ tác giả)
2. Đặt file vào thư mục `snapshots/`

**Option B: Tự tạo vector database**
```bash
# Chạy notebook để crawl và tạo embeddings
jupyter notebook rag_pipeline/notebooks/chunk_and_embedding.ipynb
```

### Bước 5: Chạy ứng dụng

```bash
# Build và start tất cả services
docker-compose up --build -d

# Kiểm tra logs
docker-compose logs -f
```

### Bước 6: Upload snapshot (nếu có)

1. Truy cập Qdrant Dashboard: http://localhost:6333/dashboard
2. Vào tab "Snapshots"
3. Upload file `medical_data.snapshot`
4. Chọn "Restore Collection"

## 🎯 Sử dụng

1. **Truy cập chatbot**: http://localhost:8501
2. **Hỏi câu hỏi y tế**: "Triệu chứng của bệnh tiểu đường là gì?"
3. **Xem kết quả**: AI sẽ trả lời với nguồn tham khảo

## 📊 Endpoints API

- **Chatbot**: http://localhost:8501 (Streamlit UI)
- **API docs**: http://localhost:8000/docs (FastAPI Swagger)
- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **Health check**: http://localhost:8000/health

## 🔧 Services

| Service | Port | Mô tả |
|---------|------|-------|
| Streamlit | 8501 | Frontend chat interface |
| FastAPI | 8000 | Backend API |
| Qdrant | 6333 | Vector database |
| PostgreSQL | 5433 | Chat history storage |

## 🐛 Troubleshooting

### Lỗi thiếu API key
```
Error: GROQ_API_KEY not found
```
**Giải pháp**: Kiểm tra file `.env` có đúng API key

### Lỗi port đã sử dụng
```
Error: port 5432 already in use
```
**Giải pháp**: Port mapping `5433:5432` đã tránh conflict

### Container không start
```bash
# Xem logs chi tiết
docker-compose logs medical-fastapi

# Restart services
docker-compose restart
```

### Không có dữ liệu trong Qdrant
1. Kiểm tra collection: http://localhost:6333/dashboard
2. Upload lại snapshot hoặc chạy notebook embedding

## 📁 Cấu trúc project

```
Medical_chatbot_by_self/
├── docker-compose.yml          # Docker orchestration
├── .env                        # Environment variables
├── rag_pipeline/              # Backend FastAPI
│   ├── Dockerfile
│   ├── src/
│   │   ├── main.py           # FastAPI app
│   │   ├── rag_pipeline.py   # RAG logic
│   │   ├── model_setup.py    # LLM setup
│   │   └── database/         # Database connections
│   └── notebooks/            # Data processing
├── streamlit/                 # Frontend
│   ├── Dockerfile
│   └── app.py                # Streamlit app
└── snapshots/                # Vector database backups
```

## 🤝 Đóng góp

1. Fork repository
2. Tạo feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push branch: `git push origin feature/amazing-feature`
5. Tạo Pull Request

## 📄 License

[MIT License](LICENSE)

## 👨‍💻 Tác giả

- **Tên**: [Your Name]
- **Email**: [your.email@domain.com]
- **GitHub**: [your-github-username]

## 🙏 Acknowledgments

- Dữ liệu y tế từ các nguồn đáng tin cậy
- Groq cho LLM API
- Qdrant cho vector database
- Streamlit cho UI framework 