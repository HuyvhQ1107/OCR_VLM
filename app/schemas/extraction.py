from pydantic import BaseModel


class ExtractionResult(BaseModel):
    id_cccd: str | None = None
    ho_ten_cccd: str | None = None
    thuong_tru_cccd: str | None = None

    loai_giay_to: str | None = None
    ten_cong_ty: str | None = None
    dia_chi_tru_so: str | None = None
    ma_so_thue: str | None = None
    so_dien_thoai: str | None = None
    email: str | None = None
    nguoi_dai_dien: str | None = None
    id_cccd_dai_dien: str | None = None
    chuc_danh: str | None = None


FIELDS: list[str] = list(ExtractionResult.model_fields.keys())
CCCD_FIELDS: list[str] = ["id_cccd", "ho_ten_cccd", "thuong_tru_cccd"]
GPKD_FIELDS: list[str] = [
    f for f in FIELDS if f not in CCCD_FIELDS and f != "loai_giay_to"
]

GROUP_FIELDS: dict[str, list[str]] = {
    "CCCD": CCCD_FIELDS,
    "GPKD": ["loai_giay_to"] + GPKD_FIELDS,
}
