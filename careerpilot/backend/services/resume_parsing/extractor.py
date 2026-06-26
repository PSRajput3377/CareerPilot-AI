"""Resume text extraction.

Isolates file-format concerns (PDF/TXT) from parsing logic. Parsers consume
plain text and never touch the filesystem or PDF internals directly.
"""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from careerpilot.backend.core.exceptions import ValidationError


def extract_text(source: str | Path) -> str:
    """Extract plain text from a resume file (.pdf or .txt).

    Raises :class:`ValidationError` for missing files or unsupported types.
    """
    path = Path(source)
    if not path.exists():
        raise ValidationError(f"Resume file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    raise ValidationError(f"Unsupported resume format '{suffix}' (use .pdf or .txt)")


def extract_text_from_bytes(data: bytes, filename: str) -> str:
    """Extract text from in-memory bytes (e.g. an HTTP upload)."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        import io

        return _read_pdf(PdfReader(io.BytesIO(data)))
    if suffix in {".txt", ".md"}:
        return data.decode("utf-8", errors="ignore")
    raise ValidationError(f"Unsupported resume format '{suffix}' (use .pdf or .txt)")


def _extract_pdf(path: Path) -> str:
    return _read_pdf(PdfReader(str(path)))


def _read_pdf(reader: PdfReader) -> str:
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(pages).strip()
    if not text:
        raise ValidationError(
            "Could not extract text from PDF (it may be scanned/image-only; OCR not supported)"
        )
    return text
