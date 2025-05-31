# Hướng dẫn chạy Medical Chatbot với Qdrant Cloud

## 1. Cài đặt dependencies

```bash
# Cài đặt tất cả thư viện cần thiết
pip install -r requirements.txt
```

## 2. Cấu hình Qdrant Cloud

### 2.1. Tạo tài khoản Qdrant Cloud
1. Truy cập https://cloud.qdrant.io/
2. Đăng ký tài khoản miễn phí
3. Tạo một cluster mới

### 2.2. Lấy thông tin kết nối
- **Cluster URL**: https://your-cluster-id.qdrant.io  
- **API Key**: Tạo trong phần API Keys

### 2.3. Tạo file .env
Tạo file `.env` trong thư mục `rag_pipeline` với nội dung:

```bash
# Qdrant Cloud Configuration
QDRANT_CLOUD_URL=https://your-cluster-id.qdrant.io
QDRANT_API_KEY=your-api-key-here

# Groq API Configuration  
GROQ_API_KEY=your-groq-api-key-here

# Collection Settings
COLLECTION_NAME=medical_data
```

## 3. Test kết nối Qdrant Cloud

```bash
cd rag_pipeline
python test_qdrant_cloud.py
```

## 4. Chạy Streamlit App

```bash
# Từ thư mục gốc project
streamlit run streamlit/app.py
```

Hoặc:

```bash
cd streamlit
streamlit run app.py
```

## 5. Sử dụng RAG Pipeline trực tiếp

```python
from rag_pipeline.src.rag_pipeline import create_rag_pipeline

# Tạo pipeline
pipeline = create_rag_pipeline()

# Truy vấn
result = pipeline.query("Triệu chứng của cúm A là gì?")
print(result['answer'])

# Xem thống kê
stats = pipeline.get_stats()
print(f"Số vectors: {stats['vector_count']}")
```

## Lỗi thường gặp

### 1. Lỗi kết nối Qdrant Cloud
- Kiểm tra QDRANT_CLOUD_URL và QDRANT_API_KEY
- Đảm bảo cluster đang hoạt động
- Kiểm tra kết nối internet

### 2. Lỗi Groq API
- Kiểm tra GROQ_API_KEY có hợp lệ không
- Kiểm tra quota còn lại tại https://console.groq.com/

### 3. Collection không tìm thấy
- Collection 'medical_data' sẽ được tự động tạo
- Nếu muốn dùng collection khác, sửa trong .env

## Upload dữ liệu mới

Xem file `data_import/upload_to_qdrant.py` để upload dữ liệu y tế mới lên Qdrant Cloud.

## Hỗ trợ

Nếu gặp vấn đề, vui lòng:
1. Kiểm tra logs trong terminal
2. Chạy test_qdrant_cloud.py để debug
3. Đảm bảo tất cả API keys đã được cấu hình đúng 