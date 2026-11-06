import base64
import io
import pymupdf as fitz  # PyMuPDF
from PIL import Image, ImageOps

from app.config import settings


def _prep(img: Image.Image, max_side: int | None = None) -> Image.Image:
    max_side = max_side or settings.MAX_SIDE
    img = ImageOps.exif_transpose(img).convert("RGB")
    w, h = img.size
    scale = max_side / max(w, h)
    if scale < 1:
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return img


def load_images(path: str) -> list[Image.Image]:
    """Đọc ảnh hoặc PDF thành danh sách PIL Image đã chuẩn hoá chiều và kích thước."""
    if path.lower().endswith(".pdf"):
        doc = fitz.open(path)
        images: list[Image.Image] = []
        try:
            for i in range(min(len(doc), settings.MAX_PDF_PAGES)):
                pix = doc[i].get_pixmap(dpi=settings.PDF_DPI)
                im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                images.append(_prep(im))
        finally:
            doc.close()
        return images

    with Image.open(path) as im:
        return [_prep(im)]


def image_to_base64(img: Image.Image) -> str:
    """Chuyển PIL Image sang chuỗi JPEG base64 để gửi qua OpenAI-compatible API."""
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=settings.JPEG_QUALITY)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def load_images_b64(path: str) -> list[str]:
    """Đọc file ảnh/PDF và trả về danh sách ảnh base64."""
    return [image_to_base64(im) for im in load_images(path)]
