"""
Script kiểm tra xem vector trong movie_vectors.npz có khớp đúng
với movie_id lấy live từ Movie Service hay không.

Chạy trực tiếp trên máy đang chạy vector_service (không qua API)
để loại trừ mọi lớp trung gian.
"""
import os
import sys
import json

# Chỉnh lại đường dẫn cho khớp với project thực tế của bạn
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scipy.sparse import load_npz, issparse
from common.config import get_config
from common.utils import ServiceClient

config = get_config()

VECTORS_PATH = os.getenv(
    'MOVIE_VECTORS_NPZ',
    'D:\Huy\Documents\KHDL\Recommend-system\movie_vectors.npz'  # sửa lại path thật nếu cần
)

TARGET_IDS = ["tt0103064", "tt0088247"]  # Terminator 2, Terminator 1
TARGET_NAMES_HINT = ["Terminator"]  # để dò theo tên nếu cần


def load_movie_ids_live():
    client = ServiceClient()
    resp = client.get(f"{config.MOVIE_SERVICE_URL}/api/movies?per_page=10000")
    data = resp.get('data', [])
    ids = [m['movie_id'] for m in data]
    names = {m['movie_id']: m.get('movie_name') for m in data}
    return ids, names


def main():
    print(f"[1] Loading vectors from: {VECTORS_PATH}")
    vectors = load_npz(VECTORS_PATH)
    if issparse(vectors):
        vectors = vectors.toarray()
    print(f"    vectors.shape = {vectors.shape}")

    print(f"[2] Fetching movie_ids live from Movie Service...")
    movie_ids, names = load_movie_ids_live()
    print(f"    len(movie_ids) = {len(movie_ids)}")

    # === Check 1: SỐ LƯỢNG có khớp không ===
    if vectors.shape[0] != len(movie_ids):
        print(f"\n❌ MISMATCH SỐ LƯỢNG: {vectors.shape[0]} vectors "
              f"nhưng {len(movie_ids)} movie_ids.")
        print("   => Gần như chắc chắn đây là nguyên nhân gây sai lệch mapping.")
    else:
        print(f"\n✅ Số lượng khớp nhau ({vectors.shape[0]}).")
        print("   (Chưa chắc thứ tự đã đúng, cần check tiếp bên dưới)")

    # === Check 2: In ra vài movie_id mục tiêu kèm index của chúng ===
    print("\n[3] Kiểm tra vị trí index của các movie_id mục tiêu:")
    id_to_index = {mid: idx for idx, mid in enumerate(movie_ids)}
    for mid in TARGET_IDS:
        idx = id_to_index.get(mid)
        name = names.get(mid, "???")
        print(f"    {mid} ({name}) -> index {idx}")

    # === Check 3: Tìm tất cả phim có tên chứa "Terminator" trong data thật ===
    print("\n[4] Tất cả phim có tên chứa 'Terminator' theo Movie Service:")
    for mid, name in names.items():
        if name and "Terminator" in name:
            idx = id_to_index.get(mid)
            print(f"    {mid} ({name}) -> index {idx}")

    print("\n[5] Nếu muốn xác minh sâu hơn: lưu lại 'movie_ids' dùng lúc build "
          "vector (nếu có file .json/.npy đi kèm lúc export) và so sánh trực "
          "tiếp với danh sách live ở trên theo TỪNG VỊ TRÍ (không chỉ theo set).")


if __name__ == '__main__':
    main()