# Family Tree Backend API

Chào mừng đến với dự án backend cho ứng dụng Quản lý Gia phả (Family Tree). Dự án này được thiết kế dựa trên **FastAPI**, cùng với hệ quản trị cơ sở dữ liệu đồ thị **Neo4j** và cơ sở dữ liệu NoSQL **MongoDB**.

## Yêu cầu hệ thống (Prerequisites)
Để chạy dự án này trên máy tính, bạn cần cài đặt:
- **Python 3.12+**
- **MongoDB** (có thể sử dụng MongoDB Atlas Cloud hoặc chạy bản local).
- **Neo4j** (có thể sử dụng Neo4j Aura Cloud hoặc chạy bản local).
- **Docker** nếu bạn muốn đóng gói và chạy ứng dụng bằng Container.

---

## Hướng dẫn Cài đặt & Chạy dự án (Local Development)

### Bước 1: Clone và di chuyển vào thư mục backend
```bash
# Mở Terminal / Command Prompt và chạy lệnh
cd backend 
```

### Bước 2: Tạo môi trường ảo (Virtual Environment)
Môi trường ảo giúp tách biệt các thư viện của dự án với hệ thống máy tính.
```bash
python -m venv .venv

# Kích hoạt trên Windows:
.venv\Scripts\activate

# Kích hoạt trên macOS/Linux:
source .venv/bin/activate
```

### Bước 3: Cài đặt các thư viện phụ thuộc
```bash
pip install -r requirements.txt
```

### Bước 4: Thiết lập biến môi trường
Tạo file cấu hình `.env` dựa trên file mẫu `.env.example`:
- Copy (hoặc sao chép tay) file `.env.example` và đổi tên nó thành `.env`.
- Mở file `.env` lên và điền các thông số kết nối Database thực tế (MongoDB, Neo4j) cũng như cấu hình SMTP (gửi mail) và JWT (xác thực token).

Ví dụ một số cấu hình quan trọng trong `.env`:
```env
# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=family_tree

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Authentication
JWT_SECRET=thay_bang_chuoi_bi_mat_cua_ban
```

### Bước 5: Khởi động Server
Bạn có thể khởi động server trực tiếp bằng lệnh `python`:
```bash
python -m app.main
```
Hoặc dùng `uvicorn` với chế độ tự động reload (hot-reload) khi code thay đổi:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Bước 6: Truy cập API Documentation (Swagger UI)
Sau khi server đã chạy (bạn sẽ thấy console báo `Application startup complete`), ứng dụng đã được thiết lập sẵn Swagger UI tại URL gốc.
Mở trình duyệt và truy cập vào: 
[http://localhost:8000/](http://localhost:8000/)

Tại đây bạn có thể xem đầy đủ danh sách các API endpoints, cấu trúc dữ liệu, và kiểm thử trực tiếp (Auth, Charts, Persons, Relationships, Tree).

---

## Hướng dẫn chạy bằng Docker (Tùy chọn)

Dự án đã có sẵn `Dockerfile`. Nếu bạn đã cài đặt Docker, bạn có thể build image và chạy container (Yêu cầu MongoDB và Neo4j cũng phải chạy ở phía Docker/Máy chủ).

```bash
# 1. Build image từ Dockerfile
docker build -t family-tree-backend .

# 2. Chạy container dựa trên image (và tự động truyền file .env)
docker run -p 8000:8000 --env-file .env family-tree-backend
```

---

## Cấu trúc thư mục chính của dự án

- **`app/`**: Thư mục chứa mã nguồn chính của API.
  - `main.py`: Điểm bắt đầu (entry point) của ứng dụng FastAPI.
  - `routers/`: Chứa các controller (endpoints) điều hướng các tính năng như xác thực (auth), đồ thị (charts), thông tin cá nhân (persons), mối quan hệ (relationships).
  - `core/`: Cấu hình chung và cài đặt (settings).
  - `db/`: Logic kết nối tới MongoDB, Neo4j.
- **`requirements.txt`**: Khai báo danh sách các thư viện Python (FastAPI, Motor, Neo4j, v.v.).
- **`Dockerfile`**: Tệp dùng để build ảnh Docker.
- **`.env.example`**: Tệp ví dụ các key môi trường mà dự án cần thiết.
