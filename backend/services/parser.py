import io

import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_bytes

def extract_text(content: bytes, filename: str) -> str:
    fname = filename.lower()

    if fname.endswith(".pdf"):
        # First, try fast text extraction with PyMuPDF
        doc = fitz.open(stream=content, filetype="pdf")
        text = "\n\n".join(page.get_text() for page in doc).strip()
        
        # If the PDF has no text layer (scanned image), fallback to OCR
        if not text:
            print("No text found by PyMuPDF. Falling back to Tesseract OCR...")
            images = convert_from_bytes(content)
            ocr_text = []
            for img in images:
                ocr_text.append(pytesseract.image_to_string(img))
            text = "\n\n".join(ocr_text).strip()
            
        return text

    if fname.endswith((".md", ".txt", ".rst")):
        return content.decode("utf-8", errors="ignore")

    return content.decode("utf-8", errors="ignore")
