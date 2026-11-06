"""Chạy toàn bộ mẫu trong tests/samples/labels.json và tính độ chính xác từng trường."""
import asyncio
import json
import sys
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.schemas.extraction import FIELDS  # noqa: E402
from app.services.merger import extract_files  # noqa: E402


def _strip_accents(s: str | None) -> str:
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", s.replace("đ", "d").replace("Đ", "D"))
    no_diacritics = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(no_diacritics.lower().split())


async def main() -> None:
    samples_dir = ROOT / "tests" / "samples"
    labels_path = samples_dir / "labels.json"
    if not labels_path.exists():
        print(f"Không tìm thấy {labels_path}")
        return

    payload = json.loads(labels_path.read_text(encoding="utf-8"))
    samples = payload.get("samples", [])
    if not samples:
        print("labels.json chưa có mẫu nào.")
        return

    exact_hits = {f: 0 for f in FIELDS}
    norm_hits = {f: 0 for f in FIELDS}
    total = len(samples)

    for item in samples:
        cccd_paths = [str(samples_dir / p) for p in item.get("cccd_files", [])]
        gpkd_paths = [str(samples_dir / p) for p in item.get("gpkd_files", [])]
        t0 = time.time()
        pred, warns = await extract_files(cccd_paths, gpkd_paths)
        dt = time.time() - t0
        pred_dict = pred.model_dump()
        expected = item.get("expected", {})
        print(f"[{item.get('name')}] {dt:.2f}s | warnings={len(warns)}")

        for f in FIELDS:
            p_val = pred_dict.get(f)
            e_val = expected.get(f)
            if p_val == e_val:
                exact_hits[f] += 1
            if _strip_accents(p_val) == _strip_accents(e_val):
                norm_hits[f] += 1

    print("\n=== ĐỘ CHÍNH XÁC THEO TRƯỜNG ===")
    print(f"{'Trường':<20} {'Khớp chính xác':<18} {'Khớp bỏ dấu'}")
    for f in FIELDS:
        ex = exact_hits[f] / total * 100
        nm = norm_hits[f] / total * 100
        print(f"{f:<20} {ex:>6.1f}%            {nm:>6.1f}%")


if __name__ == "__main__":
    asyncio.run(main())
