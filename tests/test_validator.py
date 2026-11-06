import io
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.extraction import FIELDS
from app.services.validator import normalize, pick, validate


def _make_png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (200, 120), color=(255, 255, 255)).save(buf, format="PNG")
    return buf.getvalue()


def test_normalize_rules():
    assert normalize("id_cccd", "001 099 012 345") == ("001099012345", None)
    assert normalize("id_cccd_dai_dien", "b1234567") == ("B1234567", None)
    assert normalize("ma_so_thue", "0101234567-001") == ("0101234567-001", None)
    assert normalize("so_dien_thoai", "024.3826.1234") == ("02438261234", None)
    assert normalize("email", "Contact@Example.VN ") == ("contact@example.vn", None)
    assert normalize("loai_giay_to", "ho kinh doanh") == ("HO_KINH_DOANH", None)
    val, err = normalize("loai_giay_to", "KHAC")
    assert val is None and err is not None


def test_pick_first_valid_and_ho_kinh_doanh_rule():
    val, warns = pick(
        "id_cccd",
        [("[CCCD] front.png", "12345"), ("[CCCD] back.png", "001099012345")],
        strict=True,
    )
    assert val == "001099012345"
    assert len(warns) == 1

    cleaned, _ = validate(
        {"loai_giay_to": "HO_KINH_DOANH", "chuc_danh": "Giám đốc"}
    )
    assert cleaned["chuc_danh"] == "Chủ hộ kinh doanh"


def test_api_ocr_both_and_openapi():
    client = TestClient(app)
    img_bytes = _make_png_bytes()

    # 1. Không gửi file nào -> 400
    assert client.post("/ocr/both").status_code == 400

    # 2. Chỉ gửi 1 GPKD -> 200, 3 trường CCCD là None
    r_gpkd = client.post(
        "/ocr/both",
        files=[("gpkd_files", ("gpkd_dn.png", img_bytes, "image/png"))],
    )
    assert r_gpkd.status_code == 200
    body_gpkd = r_gpkd.json()
    assert list(body_gpkd.keys()) == FIELDS
    assert body_gpkd["id_cccd"] is None
    assert body_gpkd["ho_ten_cccd"] is None
    assert body_gpkd["thuong_tru_cccd"] is None
    assert body_gpkd["loai_giay_to"] == "DOANH_NGHIEP"
    assert body_gpkd["id_cccd_dai_dien"] == "001099012345"

    # 3. Gửi cả CCCD và GPKD hộ kinh doanh -> gộp đủ 12 trường
    r_both = client.post(
        "/ocr/both",
        files=[
            ("cccd_files", ("cccd_truoc.png", img_bytes, "image/png")),
            ("gpkd_files", ("gpkd_hkd.png", img_bytes, "image/png")),
        ],
    )
    assert r_both.status_code == 200
    body_both = r_both.json()
    assert body_both["id_cccd"] == "001099012345"
    assert body_both["loai_giay_to"] == "HO_KINH_DOANH"
    assert body_both["chuc_danh"] == "Chủ hộ kinh doanh"
    assert body_both["ma_so_thue"] == "0101234567-001"

    # 4. Kiểm tra custom_openapi (OpenAPI 3.0.3, binary file array)
    spec = client.get("/openapi.json").json()
    assert spec["openapi"] == "3.0.3"
    schema = spec["components"]["schemas"]["Body_ocr_both_ocr_both_post"]
    assert "required" not in schema
    assert schema["properties"]["cccd_files"]["items"]["format"] == "binary"
    assert schema["properties"]["gpkd_files"]["items"]["format"] == "binary"
