"""Build synthetic PDF/DOCX bytes for hermetic parser tests."""

from __future__ import annotations

from io import BytesIO


def make_pdf_bytes(pages: list[str]) -> bytes:
    """Minimal PDF-1.4 with Helvetica text per page (extractable by pypdf)."""
    objects: list[bytes] = []
    # 1: Catalog, 2: Pages — filled after kids known
    page_object_numbers: list[int] = []
    content_object_numbers: list[int] = []

    # We'll assign numbers sequentially starting at 1.
    # Layout: 1 Catalog, 2 Pages, then pairs of (Page, Content) per page, then Font.
    font_num = 3 + 2 * len(pages)
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(len(pages)))

    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(
        (
            f"2 0 obj<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>endobj\n"
        ).encode()
    )

    for index, text in enumerate(pages):
        page_num = 3 + 2 * index
        content_num = page_num + 1
        page_object_numbers.append(page_num)
        content_object_numbers.append(content_num)
        safe_lines = [
            line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            for line in text.split("\n")
        ]
        commands = ["BT", "/F1 12 Tf", "72 720 Td"]
        for line_index, line in enumerate(safe_lines):
            if line_index:
                commands.append("0 -14 Td")
            commands.append(f"({line}) Tj")
        commands.append("ET")
        stream = "\n".join(commands)
        objects.append(
            (
                f"{page_num} 0 obj<< /Type /Page /Parent 2 0 R "
                f"/MediaBox [0 0 612 792] /Contents {content_num} 0 R "
                f"/Resources<< /Font<< /F1 {font_num} 0 R >> >> >>endobj\n"
            ).encode()
        )
        objects.append(
            (
                f"{content_num} 0 obj<< /Length {len(stream)} >>stream\n"
                f"{stream}\nendstream\nendobj\n"
            ).encode("latin-1", errors="replace")
        )

    objects.append(
        (
            f"{font_num} 0 obj<< /Type /Font /Subtype /Type1 "
            f"/BaseFont /Helvetica >>endobj\n"
        ).encode()
    )

    # Build xref
    offsets = [0]
    cursor = 0
    # PDF header
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    cursor = len(header)
    pieces = [header]
    for obj in objects:
        offsets.append(cursor)
        pieces.append(obj)
        cursor += len(obj)

    xref_pos = cursor
    xref_lines = [f"xref\n0 {len(offsets)}\n", "0000000000 65535 f \n"]
    for offset in offsets[1:]:
        xref_lines.append(f"{offset:010d} 00000 n \n")
    xref = "".join(xref_lines).encode()
    trailer = (
        f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n"
    ).encode()
    return b"".join(pieces) + xref + trailer


def make_encrypted_pdf_bytes() -> bytes:
    from pypdf import PdfReader, PdfWriter

    plain = make_pdf_bytes(["SYNTHETIC encrypted body"])
    reader = PdfReader(BytesIO(plain))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt("phase3-secret", algorithm="AES-256")
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def make_docx_bytes(paragraphs: list[str]) -> bytes:
    from docx import Document

    document = Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()
