"""PDF → plain text via pdfplumber."""
from __future__ import annotations

import io

import pdfplumber


def extract_text(pdf_bytes: bytes) -> str:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        parts = []
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text:
                parts.append(text)
        return "\n".join(parts).strip()
