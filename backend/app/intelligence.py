from __future__ import annotations
import io, json, re, zipfile, hashlib
from pathlib import Path
from typing import Iterable

DOC_PATTERNS = {
    "FIR": [r"\bfir\b", r"first information report"],
    "FORENSIC_REPORT": [r"forensic", r"laboratory report", r"forensic examination"],
    "WITNESS_STATEMENT": [r"witness statement", r"statement of witness", r"deposition"],
    "CHARGE_SHEET": [r"charge[- ]sheet", r"chargesheet"],
    "INVESTIGATION_REPORT": [r"investigation report", r"investigative report"],
    "COURT_FILING": [r"court filing", r"petition", r"application before the court"],
    "LEGAL_NOTICE": [r"legal notice", r"notice under"],
    "JUDGMENT": [r"judgment", r"order of the court", r"final order"],
    "EVIDENCE_RECORD": [r"evidence record", r"seized", r"chain of custody"],
}
ALLOWED_EXT = {".pdf", ".docx", ".txt", ".jpg", ".jpeg", ".png"}

PII_PATTERNS = {
    "EMAIL": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "PHONE": re.compile(r"(?<!\d)(?:\+?91[- .]?)?[6-9]\d{9}(?!\d)"),
    "AADHAAR_LIKE": re.compile(r"(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)"),
    "PAN_LIKE": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.I),
}


def safe_filename(name: str | None) -> str:
    return Path(name or "document").name.replace("/", "_").replace("\\", "_")[:120] or "document"


def validate_extension(name: str | None) -> str:
    ext = Path(name or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise ValueError("Unsupported file type. Use PDF, DOCX, TXT, JPG, JPEG or PNG.")
    return ext


def extract_text(filename: str | None, content: bytes, limit: int = 500_000) -> tuple[str, str]:
    ext = Path(filename or "").suffix.lower()
    if ext == ".txt":
        return content.decode("utf-8", "ignore")[:limit], "TEXT"
    if ext == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                xml = z.read("word/document.xml").decode("utf-8", "ignore")
            text = re.sub(r"<[^>]+>", " ", xml)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:limit], "DOCX_TEXT"
        except Exception:
            return "", "DOCX_UNAVAILABLE"
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            text = "\n".join((p.extract_text() or "") for p in reader.pages)
            return re.sub(r"\s+", " ", text).strip()[:limit], "PDF_TEXT"
        except Exception:
            return "", "PDF_OCR_UNAVAILABLE"
    if ext in {".png", ".jpg", ".jpeg"}:
        try:
            from PIL import Image
            import pytesseract
            return pytesseract.image_to_string(Image.open(io.BytesIO(content)))[:limit], "OCR"
        except Exception:
            return "", "OCR_UNAVAILABLE"
    return "", "UNSUPPORTED"


def classify_document(title: str, doc_type: str, text: str) -> tuple[str, float, list[str]]:
    haystack = f"{title} {doc_type} {text}".lower()
    scores = []
    for label, patterns in DOC_PATTERNS.items():
        hits = sum(bool(re.search(p, haystack, re.I)) for p in patterns)
        if hits:
            scores.append((hits, label))
    if not scores:
        return (doc_type.upper() if doc_type else "UNCLASSIFIED", 0.35, [])
    scores.sort(reverse=True)
    hits, label = scores[0]
    confidence = min(0.98, 0.55 + hits * 0.15)
    return label, confidence, [x[1] for x in scores[:4]]


def redact_text(text: str) -> tuple[str, list[dict]]:
    findings: list[dict] = []
    out = text
    for kind, pattern in PII_PATTERNS.items():
        matches = list(pattern.finditer(out))
        if matches:
            findings.extend({"type": kind, "value": m.group(0)} for m in matches)
            out = pattern.sub(lambda m: f"[REDACTED:{kind}]", out)
    return out, findings


def merkle_root(hashes: Iterable[str]) -> str:
    level = [h for h in hashes if h]
    if not level:
        return hashlib.sha256(b"EMPTY").hexdigest()
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [hashlib.sha256((level[i] + level[i + 1]).encode()).hexdigest() for i in range(0, len(level), 2)]
    return level[0]
