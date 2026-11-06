import os
import tempfile
import time
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from fastapi.responses import HTMLResponse
from openai import APIConnectionError, APITimeoutError

from app.config import settings
from app.schemas.extraction import ExtractionResult
from app.services.merger import extract_files

router = APIRouter()


async def _save_group(
    files: Optional[List[UploadFile]], group: str, tmp_dir: str
) -> list[str]:
    valid_files = [f for f in (files or []) if f is not None and f.filename]
    if len(valid_files) > settings.MAX_FILES_PER_GROUP:
        raise HTTPException(
            status_code=400,
            detail=f"{group}_files: tối đa {settings.MAX_FILES_PER_GROUP} file",
        )

    paths: list[str] = []
    for i, f in enumerate(valid_files):
        filename = os.path.basename(f.filename or f"{group}_{i}.jpg")
        ext = os.path.splitext(filename)[1].lower()
        if ext not in settings.ALLOWED_EXT:
            allowed_str = ", ".join(sorted(settings.ALLOWED_EXT))
            raise HTTPException(
                status_code=400,
                detail=f"{filename}: định dạng không hỗ trợ ({allowed_str})",
            )
        data = await f.read()
        if not data:
            raise HTTPException(status_code=400, detail=f"{filename}: file rỗng")
        if len(data) > settings.MAX_FILE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail=f"{filename}: vượt quá {settings.MAX_FILE_MB}MB",
            )
        safe_name = f"{group}_{i}_{filename}"
        path = os.path.join(tmp_dir, safe_name)
        with open(path, "wb") as out:
            out.write(data)
        paths.append(path)
    return paths


@router.post("/ocr/both", response_model=ExtractionResult)
async def ocr_both(
    response: Response,
    cccd_files: Optional[List[UploadFile]] = File(None),
    gpkd_files: Optional[List[UploadFile]] = File(None),
):
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp_dir:
        cccd_paths = await _save_group(cccd_files, "cccd", tmp_dir)
        gpkd_paths = await _save_group(gpkd_files, "gpkd", tmp_dir)

        if not cccd_paths and not gpkd_paths:
            raise HTTPException(
                status_code=400,
                detail="Cần ít nhất một file trong cccd_files hoặc gpkd_files",
            )

        try:
            result, warnings = await extract_files(cccd_paths, gpkd_paths)
        except (APIConnectionError, APITimeoutError) as exc:
            raise HTTPException(
                status_code=503,
                detail=f"vLLM server chưa sẵn sàng tại {settings.VLLM_BASE_URL} ({type(exc).__name__})",
            ) from exc

    response.headers["X-OCR-Warnings"] = str(len(warnings))
    response.headers["X-VLM-Mode"] = settings.VLM_MODE
    print(
        f"[ocr/both] mode={settings.VLM_MODE} cccd={len(cccd_paths)} gpkd={len(gpkd_paths)} "
        f"loai={result.loai_giay_to} warnings={len(warnings)} {time.time() - t0:.2f}s"
    )
    return result


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "mode": settings.VLM_MODE,
        "model": settings.MODEL_ID,
        "vllm_base_url": settings.VLLM_BASE_URL,
    }


@router.get("/", response_class=HTMLResponse)
async def upload_page():
    return """<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <title>OCR CCCD & Giấy phép kinh doanh</title>
  <style>
    body { font-family: system-ui, -apple-system, sans-serif; max-width: 780px; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; color: #1f2937; }
    .card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 1.25rem; background: #fff; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
    label { display: block; margin: 0.85rem 0; font-weight: 600; }
    input[type=file] { display: block; margin-top: 0.35rem; font-weight: normal; }
    button { background: #2563eb; color: #fff; border: none; padding: 0.6rem 1.2rem; border-radius: 6px; font-size: 0.95rem; cursor: pointer; }
    button:hover { background: #1d4ed8; }
    pre { background: #111827; color: #f9fafb; padding: 1rem; border-radius: 8px; white-space: pre-wrap; overflow-x: auto; }
    .meta { font-size: 0.9rem; color: #4b5563; margin-bottom: 1rem; }
    a { color: #2563eb; }
  </style>
</head>
<body>
  <h2>OCR CCCD &amp; Giấy phép kinh doanh</h2>
  <p class="meta">
    Chế độ hiện tại: <strong>""" + settings.VLM_MODE + """</strong>
    &bull; <a href="/docs">Swagger UI (/docs)</a>
    &bull; <a href="/health">Health (/health)</a>
  </p>
  <form id="f" class="card">
    <label>
      1. Ảnh/PDF CCCD (cccd_files - không bắt buộc):
      <input type="file" name="cccd_files" multiple accept="image/*,.pdf">
    </label>
    <label>
      2. Ảnh/PDF Giấy phép kinh doanh (gpkd_files - không bắt buộc):
      <input type="file" name="gpkd_files" multiple accept="image/*,.pdf">
    </label>
    <button type="submit">Trích xuất JSON</button>
  </form>
  <h3>Kết quả</h3>
  <pre id="out">Chọn ít nhất 1 file CCCD hoặc GPKD rồi bấm "Trích xuất JSON"...</pre>
  <script>
    document.getElementById("f").onsubmit = async (e) => {
      e.preventDefault();
      const out = document.getElementById("out");
      out.textContent = "Đang xử lý...";
      const fd = new FormData();
      for (const inp of e.target.querySelectorAll("input[type=file]")) {
        for (const file of inp.files) {
          fd.append(inp.name, file);
        }
      }
      const r = await fetch("/ocr/both", { method: "POST", body: fd });
      const body = await r.text();
      let formatted = body;
      try { formatted = JSON.stringify(JSON.parse(body), null, 2); } catch (_) {}
      const warns = r.headers.get("X-OCR-Warnings") || "0";
      const mode = r.headers.get("X-VLM-Mode") || "";
      out.textContent = `HTTP ${r.status} | mode=${mode} | warnings=${warns}\\n\\n${formatted}`;
    };
  </script>
</body>
</html>"""
