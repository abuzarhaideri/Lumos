import io

from pypdf import PdfReader


def extract_text(content: bytes, filename: str) -> str:
    fname = filename.lower()

    if fname.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)

    if fname.endswith((".md", ".txt", ".rst")):
        return content.decode("utf-8", errors="ignore")

    return content.decode("utf-8", errors="ignore")
