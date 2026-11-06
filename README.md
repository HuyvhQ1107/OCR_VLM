# Vietnamese Document OCR API — CCCD & Giấy phép kinh doanh (Qwen3-VL-8B)

Dịch vụ trích xuất thông tin tự động (OCR) từ ảnh chụp/bản scan/PDF của **Căn cước công dân (CCCD / Căn cước)** và **Giấy chứng nhận đăng ký doanh nghiệp / hộ kinh doanh (GPKD)** tại Việt Nam, sử dụng mô hình thị giác–ngôn ngữ **Qwen/Qwen3-VL-8B-Instruct** kết hợp với **FastAPI** và **vLLM**.

---

## Tính năng nổi bật

- **Hỗ trợ đa định dạng:** Ảnh chụp điện thoại, ảnh scan (`.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tif`, `.tiff`) và tài liệu `.pdf` nhiều trang.
- **Tách biệt rõ 2 nhóm tài liệu (`cccd_files` & `gpkd_files`):**
  - Chỉ gửi **1 GPKD** → 3 trường CCCD trả về `null`, các trường GPKD có giá trị.
  - Chỉ gửi **CCCD** (mặt trước, mặt sau) → chỉ 3 trường CCCD có giá trị.
  - Gửi **cả hai** → tự động hợp nhất thành một JSON duy nhất gồm 12 trường.
- **Chặn lẫn trường tuyệt đối:** Số CCCD của người đại diện in trên GPKD chỉ được ghi vào `id_cccd_dai_dien`, không bao giờ lọt sang `id_cccd` của thẻ CCCD cá nhân (và ngược lại).
- **Kiểm tra & chuẩn hoá bằng code (`Validator`):** Kiểm tra định dạng số CCCD (9/12 số), hộ chiếu, mã số thuế (10 số, 13 số hoặc mã chi nhánh `10 số-3 số`), số điện thoại Việt Nam, email, và tự động gán `chuc_danh = "Chủ hộ kinh doanh"` khi `loai_giay_to = "HO_KINH_DOANH"`.
- **Sẵn sàng tích hợp Frontend:** Tích hợp sẵn `CORSMiddleware`, giao diện web thử nghiệm tại `/`, và `custom_openapi` (OpenAPI 3.0.3) hiển thị nút upload nhiều file trực tiếp trên Swagger UI (`/docs`).
- **Hỗ trợ 2 chế độ chạy (`VLM_MODE`):**
  - `mock`: Chạy thử nghiệm luồng API và tích hợp Frontend trên máy **không có GPU**.
  - `vllm`: Kết nối tới server **vLLM** chạy `Qwen/Qwen3-VL-8B-Instruct` trên GPU.

---

## Cấu trúc JSON đầu ra

API `POST /ocr/both` luôn trả về đúng cấu trúc JSON 12 trường:

```json
{
  "id_cccd": "001099012345",
  "ho_ten_cccd": "NGUYỄN VĂN A",
  "thuong_tru_cccd": "Số 123 Đường Láng, Phường Láng Thượng, Quận Đống Đa, Thành phố Hà Nội",

  "loai_giay_to": "HO_KINH_DOANH",
  "ten_cong_ty": "HỘ KINH DOANH NGUYỄN VĂN A",
  "dia_chi_tru_so": "Số 45 Phố Huế, Phường Ngô Thì Nhậm, Quận Hai Bà Trưng, Thành phố Hà Nội",
  "ma_so_thue": "0101234567-001",
  "so_dien_thoai": "0912345678",
  "email": "hkd.nguyenvana@example.com",
  "nguoi_dai_dien": "NGUYỄN VĂN A",
  "id_cccd_dai_dien": "001099012345",
  "chuc_danh": "Chủ hộ kinh doanh"
}
```

| Nhóm | Trường | Mô tả |
|---|---|---|
| **CCCD** | `id_cccd` | Số định danh cá nhân (12 chữ số, hoặc 9 chữ số với CMND cũ) |
| **CCCD** | `ho_ten_cccd` | Họ và tên đầy đủ trên thẻ CCCD |
| **CCCD** | `thuong_tru_cccd` | Địa chỉ nơi thường trú / nơi cư trú trên CCCD |
| **GPKD** | `loai_giay_to` | `"DOANH_NGHIEP"`, `"HO_KINH_DOANH"`, hoặc `null` |
| **GPKD** | `ten_cong_ty` | Tên doanh nghiệp (tiếng Việt) hoặc tên hộ kinh doanh |
| **GPKD** | `dia_chi_tru_so` | Địa chỉ trụ sở chính / địa chỉ trụ sở hộ kinh doanh |
| **GPKD** | `ma_so_thue` | Mã số doanh nghiệp / mã số thuế / mã số chi nhánh (`xxxxxxxxxx-xxx`) |
| **GPKD** | `so_dien_thoai` | Số điện thoại trên GPKD |
| **GPKD** | `email` | Địa chỉ email trên GPKD |
| **GPKD** | `nguoi_dai_dien` | Người đại diện theo pháp luật / Chủ hộ kinh doanh / Chủ doanh nghiệp |
| **GPKD** | `id_cccd_dai_dien` | Số CCCD/CMND/Hộ chiếu của người đại diện ghi trong GPKD |
| **GPKD** | `chuc_danh` | Chức danh người đại diện (luôn là `"Chủ hộ kinh doanh"` nếu là `HO_KINH_DOANH`) |

---

## Kiến trúc hệ thống

```
Client / Frontend ──▶ FastAPI (:8000) ──▶ vLLM Server (:8001, Qwen/Qwen3-VL-8B-Instruct) ──▶ JSON
```

---

## Tiêu chuẩn GPU & Yêu cầu phần cứng

Dự án sử dụng mô hình **Qwen/Qwen3-VL-8B-Instruct** (~8 tỷ tham số). Tuỳ thuộc vào môi trường triển khai, yêu cầu cấu hình GPU như sau:

| Phân khúc | GPU khuyến nghị | VRAM tối thiểu | Chế độ nạp (Precision) | Thời gian xử lý dự kiến | Phù hợp cho |
|---|---|---|---|---|---|
| **Production (Khuyến nghị)** | **NVIDIA A100** (40GB / 80GB) hoặc **L40S / RTX 6000 Ada** | **≥ 24GB – 32GB** | `bfloat16` (qua **vLLM**) | **3 – 6 giây / request** (chạy song song nhiều file) | Hệ thống thực tế, chịu tải nhiều request đồng thời, độ chính xác cao nhất |
| **Tầm trung / Colab Pro** | **NVIDIA L4** (24GB), **RTX 3090 / 4090** (24GB) | **24GB** | `bfloat16` (qua **vLLM**) | **5 – 10 giây / request** | Server nội bộ vừa và nhỏ, môi trường staging |
| **Thử nghiệm / Colab Free** | **NVIDIA T4** (16GB) hoặc **RTX 4070 / 4080** (12–16GB) | **12GB – 16GB** | **4-bit NF4** (`bitsandbytes` hoặc `AWQ`) | **15 – 40 giây / file** | Thử nghiệm miễn phí trên Google Colab, kiểm tra prompt |
| **Dev Frontend (Không GPU)** | Không cần GPU (CPU bất kỳ) | **RAM ≥ 4GB** | `VLM_MODE=mock` | **< 0.1 giây** | Lập trình viên ghép nối giao diện, kiểm thử luồng API & Validator |

### Lưu ý kỹ thuật về GPU:
- **Kiến trúc GPU:** Để chạy chế độ `bfloat16` đầy đủ và đạt tốc độ tối ưu với FlashAttention-2, GPU cần có **Compute Capability ≥ 8.0** (kiến trúc **Ampere, Ada Lovelace, Hopper** như A100, L4, A10G, RTX 30xx/40xx).
- **Dung lượng VRAM ở `bfloat16`:** Riêng bộ trọng số `Qwen3-VL-8B` chiếm khoảng **17GB – 18GB VRAM**; phần VRAM còn lại (tối thiểu 6GB – 14GB) dùng cho KV Cache để xử lý ảnh độ phân giải cao (`1600px`) và PDF nhiều trang (`--max-model-len 16384`).
- **Với GPU thế hệ cũ (Compute Capability < 8.0 như Tesla T4, V100):** Không hỗ trợ `bfloat16` phần cứng tốt, notebook sẽ tự động chuyển sang nén **4-bit (`nf4`)** hoặc dùng `float16`.

---

## Cấu trúc thư mục

```text
├── app/
│   ├── main.py                 # Khởi tạo FastAPI, CORSMiddleware, custom_openapi (OpenAPI 3.0.3)
│   ├── config.py               # Quản lý cấu hình từ file .env
│   ├── api/
│   │   └── routes.py           # POST /ocr/both, GET /health, GET / (trang upload thử)
│   ├── schemas/
│   │   └── extraction.py       # Pydantic schema ExtractionResult (12 trường)
│   ├── services/
│   │   ├── preprocess.py       # Đọc ảnh/PDF (PyMuPDF), xoay EXIF, resize, mã hoá base64
│   │   ├── extractor.py        # Gọi vLLM (OpenAI-compatible API) hoặc chạy chế độ mock
│   │   ├── validator.py        # Chuẩn hoá và kiểm tra định dạng từng trường
│   │   └── merger.py           # Xử lý theo nhóm file, chặn lẫn trường và gộp kết quả
│   └── prompts/
│       └── extract.txt         # System prompt (PROMPT_BOTH) cho Qwen3-VL
├── notebooks/
│   └── ocr_cccd_gpkd_qwen3vl_colab.ipynb  # Notebook chạy trực tiếp trên Google Colab (T4 / L4 / A100)
├── scripts/
│   └── evaluate.py             # Đánh giá độ chính xác theo từng trường trên tập mẫu
├── tests/
│   ├── samples/                # Ảnh mẫu + labels.json
│   └── test_validator.py       # Unit test cho validator, merger và API
├── Dockerfile
├── docker-compose.yml          # Triển khai đồng thời vLLM + FastAPI
├── requirements.txt
└── .env.example
```

---

## Hướng dẫn cài đặt & chạy dự án

### 1. Chạy local (chế độ `mock` khi máy không có GPU, hoặc kết nối vLLM từ xa)

```bash
# 1. Tạo môi trường ảo và cài đặt thư viện
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt

# 2. Tạo file cấu hình .env
cp .env.example .env

# 3. Khởi chạy FastAPI server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Sau khi chạy, mở trình duyệt tại:
- **Giao diện upload thử:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Healthcheck:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

### 2. Chạy với GPU thật bằng vLLM

Trên máy chủ Linux có GPU (khuyến nghị L4 / A100 chạy `bfloat16`):

```bash
# Khởi chạy vLLM server ở cổng 8001
vllm serve Qwen/Qwen3-VL-8B-Instruct \
  --dtype bfloat16 \
  --max-model-len 16384 \
  --gpu-memory-utilization 0.85 \
  --limit-mm-per-prompt '{"image": 4}' \
  --enable-prefix-caching \
  --port 8001
```

Cập nhật file `.env` của FastAPI:

```ini
VLM_MODE=vllm
VLLM_BASE_URL=http://localhost:8001/v1
MODEL_ID=Qwen/Qwen3-VL-8B-Instruct
```

Hoặc chạy trọn gói bằng **Docker Compose**:

```bash
docker compose up -d
```

---

### 3. Chạy trên Google Colab (T4 miễn phí hoặc L4/A100)

Mở file [`notebooks/ocr_cccd_gpkd_qwen3vl_colab.ipynb`](notebooks/ocr_cccd_gpkd_qwen3vl_colab.ipynb) trên Google Colab:
1. Chọn `Runtime` → `Change runtime type` → `GPU` (T4 tự động bật nén 4-bit `nf4`; L4/A100 chạy `bfloat16`).
2. Chạy lần lượt các cell từ trên xuống để tải model và trích xuất trực tiếp hoặc mở FastAPI ngay trong Colab.

---

## Sử dụng API

### `POST /ocr/both` (`multipart/form-data`)

- `cccd_files` *(tùy chọn, nhiều file)*: Ảnh/PDF mặt trước, mặt sau CCCD.
- `gpkd_files` *(tùy chọn, nhiều file)*: Ảnh/PDF Giấy chứng nhận đăng ký doanh nghiệp / hộ kinh doanh.
- *(Phải gửi ít nhất 1 file ở một trong hai trường).*

#### Ví dụ gọi bằng `curl`:

```bash
curl -X POST "http://127.0.0.1:8000/ocr/both" \
  -F "cccd_files=@tests/samples/sample_cccd.png" \
  -F "gpkd_files=@tests/samples/sample_gpkd_hkd.png"
```

#### Ví dụ gọi chỉ 1 file GPKD:

```bash
curl -X POST "http://127.0.0.1:8000/ocr/both" \
  -F "gpkd_files=@tests/samples/sample_gpkd_hkd.png"
```

---

## Kiểm thử & Đánh giá chất lượng

```bash
# Chạy unit test (validator, merger, API, OpenAPI schema)
python -m pytest tests/test_validator.py -v

# Chạy đánh giá độ chính xác từng trường trên bộ mẫu trong tests/samples/labels.json
python scripts/evaluate.py
```

---

## Bảo mật dữ liệu cá nhân

- **Không lưu trữ ảnh gốc:** Mọi file upload được xử lý trong thư mục tạm (`tempfile.TemporaryDirectory`) và tự động xoá sạch ngay khi kết thúc request.
- **Không ghi dữ liệu nhạy cảm vào log:** Server chỉ ghi log thời gian xử lý và số lượng file, không ghi số CCCD, họ tên hay địa chỉ ra terminal.
- **Không commit ảnh thật lên Git:** `.gitignore` đã chặn sẵn các file ảnh/PDF trong `tests/samples/`.
