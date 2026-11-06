import asyncio
import os
from typing import Any

from app.config import settings
from app.schemas.extraction import ExtractionResult, FIELDS, GROUP_FIELDS
from app.services.extractor import extract_single_file
from app.services.preprocess import load_images_b64
from app.services.validator import clean_value, pick

_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(settings.MAX_CONCURRENCY)
    return _semaphore


async def _process_one(path: str, group: str) -> tuple[str, dict[str, Any] | None, str | None]:
    name = f"[{group}] {os.path.basename(path)}"
    try:
        images_b64 = await asyncio.to_thread(load_images_b64, path)
    except Exception as e:
        return name, None, f"{name}: không mở được file ({type(e).__name__})"

    if not images_b64:
        return name, None, f"{name}: file không có trang nào"

    async with _get_semaphore():
        data = await extract_single_file(path, group, images_b64)

    if not data:
        return name, None, f"{name}: model không trả về JSON hợp lệ"
    return name, data, None


async def extract_group(
    paths: list[str], group: str
) -> tuple[dict[str, list[tuple[str, Any]]], list[str]]:
    """Chạy trích xuất cho các file trong một nhóm ('CCCD' hoặc 'GPKD') và chặn lẫn trường."""
    allowed = GROUP_FIELDS[group]
    others = [f for f in FIELDS if f not in allowed]
    cands: dict[str, list[tuple[str, Any]]] = {k: [] for k in allowed}
    warns: list[str] = []

    outcomes = await asyncio.gather(*(_process_one(p, group) for p in paths))

    for name, data, err in outcomes:
        if err:
            warns.append(err)
            continue
        assert data is not None

        leaked = [k for k in others if clean_value(data.get(k)) is not None]
        got = [k for k in allowed if clean_value(data.get(k)) is not None]
        if leaked:
            warns.append(f"{name}: bỏ {', '.join(leaked)} vì file thuộc nhóm {group}")
        if not got:
            hint = (
                " (nội dung có vẻ thuộc nhóm khác, kiểm tra lại file)"
                if leaked
                else ""
            )
            warns.append(f"{name}: không đọc được trường nào của nhóm {group}{hint}")
        for k in got:
            cands[k].append((name, data[k]))

    return cands, warns


async def extract_files(
    cccd_paths: list[str] | tuple[str, ...] = (),
    gpkd_paths: list[str] | tuple[str, ...] = (),
    strict: bool | None = None,
) -> tuple[ExtractionResult, list[str]]:
    """Đọc nhóm CCCD và nhóm GPKD rồi gộp thành một ExtractionResult đúng cấu trúc."""
    result: dict[str, str | None] = {k: None for k in FIELDS}
    warnings: list[str] = []

    for group, paths in (("CCCD", list(cccd_paths)), ("GPKD", list(gpkd_paths))):
        if not paths:
            continue
        cands, w = await extract_group(paths, group)
        warnings.extend(w)
        for k, c in cands.items():
            val, w_pick = pick(k, c, strict=strict)
            result[k] = val
            warnings.extend(w_pick)

    if result["loai_giay_to"] == "HO_KINH_DOANH":
        result["chuc_danh"] = "Chủ hộ kinh doanh"

    return ExtractionResult(**result), warnings
