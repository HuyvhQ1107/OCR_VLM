import json
import os
import re
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from app.config import settings
from app.schemas.extraction import ExtractionResult

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "extract.txt"
PROMPT_BOTH = PROMPT_PATH.read_text(encoding="utf-8")

HINTS: dict[str, str] = {
    "CCCD": """
========================
GỢI Ý NHÓM FILE
========================

Các ảnh dưới đây ĐỀU LÀ CCCD/Căn cước (mặt trước và/hoặc mặt sau).
Chỉ điền id_cccd, ho_ten_cccd, thuong_tru_cccd.
Tất cả trường còn lại (kể cả loai_giay_to) = null.
""",
    "GPKD": """
========================
GỢI Ý NHÓM FILE
========================

Các ảnh dưới đây ĐỀU LÀ giấy chứng nhận đăng ký doanh nghiệp / hộ kinh doanh (có thể nhiều trang).
id_cccd, ho_ten_cccd, thuong_tru_cccd = null.
Số CCCD/CMND/Hộ chiếu của người đại diện ghi vào id_cccd_dai_dien.
""",
}

EXTRACTION_JSON_SCHEMA = ExtractionResult.model_json_schema()


def build_prompt(group: str) -> str:
    return PROMPT_BOTH + HINTS[group]


def parse_json(text: str) -> dict[str, Any]:
    if not text:
        return {}
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {}
    try:
        data = json.loads(m.group(0))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            base_url=settings.VLLM_BASE_URL,
            api_key=settings.VLLM_API_KEY,
            timeout=settings.VLM_TIMEOUT_SECONDS,
            max_retries=1,
        )
    return _client


async def call_vlm(
    images_b64: list[str],
    prompt: str,
    json_schema: dict[str, Any] = EXTRACTION_JSON_SCHEMA,
) -> str:
    """Gọi vLLM server qua OpenAI-compatible API theo mục 6 của kế hoạch."""
    client = get_openai_client()
    content: list[dict[str, Any]] = [
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b}"}}
        for b in images_b64
    ]
    content.append({"type": "text", "text": prompt})
    resp = await client.chat.completions.create(
        model=settings.MODEL_ID,
        messages=[{"role": "user", "content": content}],
        temperature=0,
        max_tokens=settings.VLM_MAX_TOKENS,
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "extraction", "schema": json_schema},
        },
    )
    return resp.choices[0].message.content or "{}"


def mock_vlm_response(filename: str, group: str) -> dict[str, Any]:
    """Giả lập kết quả model khi VLM_MODE=mock (chạy thử trên máy không có GPU)."""
    low = os.path.basename(filename).lower()

    # Hỗ trợ test trường hợp gửi nhầm loại file vào nhóm
    if "wrong" in low:
        if group == "GPKD":
            return {
                "id_cccd": "001203009999",
                "ho_ten_cccd": "LÊ VĂN C",
                "thuong_tru_cccd": "Số 10, Phường Láng Thượng, Quận Đống Đa, Hà Nội",
            }
        return {
            "loai_giay_to": "DOANH_NGHIEP",
            "ten_cong_ty": "CÔNG TY TNHH THỬ NGHIỆM",
            "ma_so_thue": "0101234567",
        }

    if group == "CCCD":
        if "sau" in low or "back" in low:
            return {
                "id_cccd": None,
                "ho_ten_cccd": None,
                "thuong_tru_cccd": "Số 123 Đường Láng, Phường Láng Thượng, Quận Đống Đa, Thành phố Hà Nội",
            }
        return {
            "id_cccd": "001099012345",
            "ho_ten_cccd": "NGUYỄN VĂN A",
            "thuong_tru_cccd": "Số 123 Đường Láng, Phường Láng Thượng, Quận Đống Đa, Thành phố Hà Nội",
        }

    # Nhóm GPKD: nếu tên file có "hkd" hoặc "ho_kinh_doanh" thì giả lập hộ kinh doanh
    if "hkd" in low or "ho_kinh_doanh" in low:
        return {
            "loai_giay_to": "HO_KINH_DOANH",
            "ten_cong_ty": "HỘ KINH DOANH NGUYỄN VĂN A",
            "dia_chi_tru_so": "Số 45 Phố Huế, Phường Ngô Thì Nhậm, Quận Hai Bà Trưng, Thành phố Hà Nội",
            "ma_so_thue": "0101234567-001",
            "so_dien_thoai": "0912345678",
            "email": "hkd.nguyenvana@example.com",
            "nguoi_dai_dien": "NGUYỄN VĂN A",
            "id_cccd_dai_dien": "001099012345",
            "chuc_danh": "Chủ hộ kinh doanh",
        }

    return {
        "loai_giay_to": "DOANH_NGHIEP",
        "ten_cong_ty": "CÔNG TY TNHH CÔNG NGHỆ MẪU VIỆT NAM",
        "dia_chi_tru_so": "Tầng 5, Tòa nhà ABC, Số 10 Đường Cầu Giấy, Phường Quan Hoa, Quận Cầu Giấy, Thành phố Hà Nội",
        "ma_so_thue": "0109876543",
        "so_dien_thoai": "02438261234",
        "email": "contact@congnghemau.vn",
        "nguoi_dai_dien": "NGUYỄN VĂN A",
        "id_cccd_dai_dien": "001099012345",
        "chuc_danh": "Giám đốc",
    }


async def extract_single_file(path: str, group: str, images_b64: list[str]) -> dict[str, Any]:
    """Trích xuất một file theo chế độ VLM_MODE ('mock' hoặc 'vllm')."""
    if settings.VLM_MODE == "mock":
        return mock_vlm_response(path, group)

    prompt = build_prompt(group)
    raw_text = await call_vlm(images_b64, prompt, EXTRACTION_JSON_SCHEMA)
    return parse_json(raw_text)
