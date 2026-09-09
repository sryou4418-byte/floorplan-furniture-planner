from __future__ import annotations

from io import BytesIO

import fitz
from PIL import Image, UnidentifiedImageError


MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 30_000_000


def normalize_plan(data: bytes, filename: str) -> tuple[bytes, str]:
    if not data:
        raise ValueError("빈 파일은 사용할 수 없습니다.")
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("도면 파일은 20MB 이하여야 합니다.")

    if filename.lower().endswith(".pdf"):
        try:
            document = fitz.open(stream=data, filetype="pdf")
            if document.page_count < 1:
                raise ValueError("페이지가 없는 PDF입니다.")
            page = document.load_page(0)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            png = pixmap.tobytes("png")
            document.close()
            _verify_image(png)
            return png, "image/png"
        except (fitz.FileDataError, RuntimeError) as exc:
            raise ValueError("올바른 PDF 도면이 아닙니다.") from exc

    _verify_image(data)
    with Image.open(BytesIO(data)) as image:
        image.thumbnail((5000, 5000))
        output = BytesIO()
        image.convert("RGB").save(output, format="JPEG", quality=90, optimize=True)
    return output.getvalue(), "image/jpeg"


def _verify_image(data: bytes) -> None:
    try:
        with Image.open(BytesIO(data)) as image:
            width, height = image.size
            if width * height > MAX_PIXELS:
                raise ValueError("도면 해상도가 너무 큽니다.")
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("올바른 이미지 파일이 아닙니다.") from exc
