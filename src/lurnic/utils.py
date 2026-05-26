# src/lurnic/utils.py
"""
Utility functions for Lurnic - PDF extraction, image rendering, and page analysis
"""

import PyPDF2
import pdfplumber
import re
import os
import io
from typing import List, Dict, Tuple
import fitz  # PyMuPDF - for PDF page rendering
from PIL import Image

# ================================================================
# TEXT EXTRACTION (FOR FREE TIER)
# ================================================================

def extract_text_pdfplumber(pdf_bytes: bytes) -> str:
    """Extract text using pdfplumber (good for digital PDFs)"""
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                if page_text:
                    text += f"\n--- Page {page_num + 1} ---\n"
                    text += page_text
    except Exception as e:
        print(f"pdfplumber extraction error: {e}")
        return ""
    return text


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF (for free tier)"""
    if not pdf_bytes:
        return ""
    
    text = extract_text_pdfplumber(pdf_bytes)
    if len(text.strip()) < 100:
        # Try PyPDF2 as fallback
        try:
            text = ""
            reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                if page_text:
                    text += f"\n--- Page {page_num + 1} ---\n"
                    text += page_text
        except Exception as e:
            print(f"PyPDF2 extraction error: {e}")
    
    return text


def chunk_text(text: str, chunk_size: int = 5000, overlap: int = 500) -> List[str]:
    """Split text into overlapping chunks"""
    if not text:
        return []
    
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        word_length = len(word) + 1
        
        if current_length + word_length > chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            
            if overlap > 0 and len(current_chunk) > overlap:
                overlap_words = current_chunk[-overlap:]
            else:
                overlap_words = current_chunk.copy()
            
            current_chunk = overlap_words.copy()
            current_length = sum(len(w) + 1 for w in current_chunk)
        
        current_chunk.append(word)
        current_length += word_length
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks


def clean_text(text: str) -> str:
    """Clean extracted text"""
    if not text:
        return ""
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return '\n'.join(lines)


# ================================================================
# PDF PAGE RENDERING (FOR PAID TIER - IMAGES)
# ================================================================

def render_page_to_image(pdf_bytes: bytes, page_num: int, dpi: int = 150) -> bytes:
    """Convert a single PDF page to PNG image bytes"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc.load_page(page_num)
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img_bytes = pix.tobytes("png")
    doc.close()
    return img_bytes


def render_all_pages_to_images(pdf_bytes: bytes, dpi: int = 150, max_pages: int = 30) -> List[bytes]:
    """Convert all PDF pages to PNG images (limited to max_pages)"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    total_pages = min(len(doc), max_pages)
    
    for page_num in range(total_pages):
        page = doc.load_page(page_num)
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_bytes = pix.tobytes("png")
        images.append(img_bytes)
    
    doc.close()
    return images


# ================================================================
# PAGE ANALYSIS (FOR SMART HYBRID - DETECT WHERE IMAGES ARE NEEDED)
# ================================================================

def analyze_page_needs_vision(pdf_bytes: bytes, page_num: int) -> bool:
    """
    Determine if a PDF page needs image-based processing.
    
    Returns True if page has:
    - Embedded images/diagrams
    - Tables
    - Low text density (suggesting image-heavy page)
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc.load_page(page_num)
    
    # Check for embedded images
    images = page.get_images()
    has_images = len(images) > 0
    
    # Check for tables (using pdfplumber)
    has_table = False
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            if page_num < len(pdf.pages):
                tables = pdf.pages[page_num].extract_tables()
                has_table = len(tables) > 0 and any(tables[0])
    except:
        pass
    
    # Check text density
    text = page.get_text()
    text_length = len(text.strip())
    
    # Page area approximation
    rect = page.rect
    page_area = rect.width * rect.height
    text_density = text_length / page_area if page_area > 0 else 0
    
    # Low density + small text = likely image-heavy
    is_image_heavy = text_density < 0.05 and text_length < 200
    
    doc.close()
    
    return has_images or has_table or is_image_heavy


def get_pages_that_need_vision(pdf_bytes: bytes, max_pages: int = 15) -> List[int]:
    """
    Get list of page numbers that need image-based processing.
    Limited to max_pages to control costs.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = len(doc)
    doc.close()
    
    needs_vision = []
    for page_num in range(min(total_pages, 50)):  # Only check first 50 pages
        if analyze_page_needs_vision(pdf_bytes, page_num):
            needs_vision.append(page_num)
        if len(needs_vision) >= max_pages:
            break
    
    return needs_vision


# ================================================================
# PDF METADATA
# ================================================================

def get_pdf_metadata(pdf_bytes: bytes) -> Dict:
    """Extract PDF metadata"""
    metadata = {
        "page_count": 0,
        "file_size_mb": 0,
        "filename": "unknown"
    }
    
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        metadata["page_count"] = len(doc)
        doc.close()
        
        metadata["file_size_mb"] = round(len(pdf_bytes) / (1024 * 1024), 2)
    except Exception as e:
        print(f"Metadata error: {e}")
    
    return metadata


print("✓ utils.py loaded successfully (with multimodal support)")