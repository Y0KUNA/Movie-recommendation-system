# MovieDB - Trang Web Xem Thông Tin Phim

Trang web xem thông tin phim với giao diện giống IMDB, sử dụng dữ liệu từ file `action.csv`.

## Tính năng

- 🔍 Tìm kiếm phim theo tên, đạo diễn, thể loại
- 📋 Hiển thị danh sách phim dạng lưới (grid)
- 📄 Xem chi tiết thông tin từng bộ phim
- 📱 Giao diện responsive, đẹp mắt
- ⭐ Hiển thị rating, năm sản xuất, thể loại, diễn viên...

## Cài đặt

1. Cài đặt Python dependencies:
```bash
pip install -r requirements.txt
```

2. Đảm bảo file `action.csv` có trong thư mục gốc của project.

## Chạy ứng dụng

```bash
python app.py
```

Sau đó mở trình duyệt và truy cập: `http://localhost:5000`

## Cấu trúc project

```
Recommend-system/
├── app.py              # Flask backend
├── action.csv          # Dữ liệu phim
├── requirements.txt    # Python dependencies
├── templates/          # HTML templates
│   └── index.html
└── static/            # CSS và JavaScript
    ├── style.css
    └── script.js
```

## API Endpoints

- `GET /` - Trang chủ
- `GET /api/movies?page=1&per_page=20&search=...` - Lấy danh sách phim
- `GET /api/movies/<movie_id>` - Lấy thông tin chi tiết phim

