import re
from typing import Any

from app.config import settings
from app.schemas.extraction import FIELDS

LOAI_HOP_LE = {"DOANH_NGHIEP", "HO_KINH_DOANH"}
EMPTY_WORDS = {"", "null", "none", "n/a", "không có", "khong co"}

RE_MST = re.compile(r"\d{10}(-\d{3})?|\d{13}")
RE_PHONE = re.compile(r"(\+84|0)\d{8,10}")
RE_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
RE_PASSPORT = re.compile(r"[A-Z]\d{7,8}")


def clean_value(v: Any) -> str | None:
    if v is None:
        return None
    s = re.sub(r"\s+", " ", str(v)).strip()
    return None if s.lower() in EMPTY_WORDS else s


def normalize(field: str, v: Any) -> tuple[str | None, str | None]:
    """Chuẩn hoá một trường. Trả về (giá_trị_chuẩn_hoá, thông_báo_lỗi_nếu_có)."""
    s = clean_value(v)
    if s is None:
        return None, None

    if field == "loai_giay_to":
        u = re.sub(r"[\s\-]+", "_", s).upper()
        if u in LOAI_HOP_LE:
            return u, None
        return None, f"giá trị không hợp lệ ({s!r}), đặt null"

    if field in ("id_cccd", "id_cccd_dai_dien"):
        compact = re.sub(r"[\s.\-]", "", s).upper()
        if field == "id_cccd_dai_dien" and RE_PASSPORT.fullmatch(compact):
            return compact, None
        digits = re.sub(r"\D", "", s)
        if len(digits) in (9, 12):
            return digits, None
        extra = ", hoặc số hộ chiếu" if field == "id_cccd_dai_dien" else ""
        return digits or s, f"kỳ vọng 12 số (hoặc 9 số với CMND cũ{extra}) ({s!r})"

    if field == "ma_so_thue":
        v2 = re.sub(r"[\s.]", "", s)
        if RE_MST.fullmatch(v2):
            return v2, None
        return v2, f"kỳ vọng 10 hoặc 13 chữ số, hoặc dạng 10 số-3 số ({s!r})"

    if field == "so_dien_thoai":
        v2 = re.sub(r"[\s.\-()]", "", s)
        if RE_PHONE.fullmatch(v2):
            return v2, None
        return v2, f"không giống số điện thoại Việt Nam ({s!r})"

    if field == "email":
        v2 = s.lower().replace(" ", "")
        if RE_EMAIL.fullmatch(v2):
            return v2, None
        return v2, f"sai định dạng ({s!r})"

    return s, None


def pick(
    field: str,
    candidates: list[tuple[str, Any]],
    strict: bool | None = None,
) -> tuple[str | None, list[str]]:
    """Chọn giá trị hợp lệ đầu tiên trong danh sách ứng viên [(tên_file, giá_trị)]."""
    strict = settings.STRICT if strict is None else strict
    fallback: str | None = None
    warns: list[str] = []

    for name, raw in candidates:
        val, err = normalize(field, raw)
        if val is not None and err is None:
            return val, warns
        if err:
            warns.append(f"{name}: {field}: {err}")
        if fallback is None and val is not None:
            fallback = val

    if fallback is not None and not strict:
        return fallback, warns
    return None, warns


def validate(
    data: dict[str, Any], strict: bool | None = None
) -> tuple[dict[str, str | None], list[str]]:
    """Kiểm tra và chuẩn hoá một dict kết quả đã gộp."""
    strict = settings.STRICT if strict is None else strict
    d: dict[str, str | None] = {}
    warnings: list[str] = []

    for f in FIELDS:
        val, err = normalize(f, data.get(f))
        if err:
            warnings.append(f"{f}: {err}")
            d[f] = None if strict else val
        else:
            d[f] = val

    if d.get("loai_giay_to") == "HO_KINH_DOANH":
        d["chuc_danh"] = "Chủ hộ kinh doanh"

    return d, warnings
