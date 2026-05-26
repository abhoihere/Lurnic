# src/lurnic/core.py
"""
Core Lurnic logic - Free tier (text only) and Paid tier (text + selective images)
"""

from google import genai
from typing import List, Dict, Optional
import time
import io

from .config import Config
from .utils import (
    extract_text_from_pdf,
    chunk_text,
    clean_text,
    get_pdf_metadata,
    render_page_to_image,
    get_pages_that_need_vision
)

# Initialize Gemini client
client = genai.Client(api_key=Config.GEMINI_API_KEY)


# ================================================================
# TEXT-ONLY FUNCTIONS (FREE TIER)
# ================================================================

def ask_gemini_with_text(question: str, context: str, model: str = None) -> str:
    """Send text-only question to Gemini (used by free tier)"""
    if model is None:
        model = Config.MODEL_FREE
    
    prompt = f"""You are Lurnic, an AI study assistant.

CONTEXT (from textbook):
{context}

STUDENT QUESTION:
{question}

INSTRUCTIONS:
1. Answer based ONLY on the context above.
2. If the answer is not in the context, say "I cannot find this information."
3. Be clear and educational.

ANSWER:
"""
    
    try:
        response = client.models.generate_content(model=model, contents=prompt)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"


def process_pdf_free(pdf_bytes: bytes, question: str) -> Dict:
    """
    Process PDF for FREE tier - text extraction only.
    Cost: ~$0.08 per book.
    """
    start_time = time.time()
    
    # Extract text
    full_text = extract_text_from_pdf(pdf_bytes)
    
    if not full_text or len(full_text.strip()) < 100:
        return {
            "answer": "Could not extract text from this PDF. It may be scanned or image-based. Please upgrade to paid tier for image support.",
            "method_used": "text_only_failed",
            "pages_processed": 0,
            "processing_time": time.time() - start_time
        }
    
    # Clean and chunk
    clean_full_text = clean_text(full_text)
    chunks = chunk_text(clean_full_text, chunk_size=Config.CHUNK_SIZE, overlap=Config.CHUNK_OVERLAP)
    
    # Combine chunks for context
    combined_context = "\n\n--- SECTION BREAK ---\n\n".join(chunks[:10])  # Limit to 10 chunks
    
    # Get answer
    answer = ask_gemini_with_text(question, combined_context, model=Config.MODEL_FREE)
    
    return {
        "answer": answer,
        "method_used": "text_only",
        "chunks_processed": len(chunks),
        "pages_processed": len(full_text.split("--- Page")),
        "processing_time": round(time.time() - start_time, 2)
    }


# ================================================================
# MULTIMODAL FUNCTIONS (PAID TIER - IMAGES)
# ================================================================

def ask_gemini_with_image(image_bytes: bytes, question: str, thinking_level: str = None) -> str:
    """Send a single image to Gemini (for diagrams, charts, etc.)"""
    if thinking_level is None:
        thinking_level = Config.THINKING_LEVEL_PAID
    
    try:
        response = client.models.generate_content(
            model=Config.MODEL_PAID,
            contents=[question, 
                      genai.types.Part.from_bytes(data=image_bytes, mime_type="image/png")],
            config={"thinking_config": {"type": thinking_level}} if thinking_level else None
        )
        return response.text
    except Exception as e:
        return f"Error processing image: {str(e)}"


def ask_gemini_with_multiple_images(images: List[bytes], question: str, thinking_level: str = None) -> str:
    """Send multiple images to Gemini (up to 15 pages)"""
    if thinking_level is None:
        thinking_level = Config.THINKING_LEVEL_PAID
    
    contents = [question]
    for img_bytes in images[:Config.MAX_IMAGE_PAGES_PER_REQUEST]:
        contents.append(genai.types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
    
    try:
        response = client.models.generate_content(
            model=Config.MODEL_PAID,
            contents=contents,
            config={"thinking_config": {"type": thinking_level}} if thinking_level else None
        )
        return response.text
    except Exception as e:
        return f"Error processing images: {str(e)}"


def process_pdf_paid(pdf_bytes: bytes, question: str) -> Dict:
    """
    Process PDF for PAID tier - HYBRID approach:
    - Extract text for most pages (cheap)
    - Send only image-heavy pages as images (selective)
    
    Cost: ~$0.10-0.15 per book (vs $0.25 for pure image)
    """
    start_time = time.time()
    
    # Step 1: Extract text from all pages (cheap baseline)
    full_text = extract_text_from_pdf(pdf_bytes)
    metadata = get_pdf_metadata(pdf_bytes)
    
    # Step 2: Identify pages that need vision (images, tables, diagrams)
    pages_needing_vision = get_pages_that_need_vision(pdf_bytes, max_pages=15)
    
    # Step 3: Process text context (cheap)
    text_answer = ""
    if full_text and len(full_text.strip()) > 100:
        clean_full_text = clean_text(full_text)
        chunks = chunk_text(clean_full_text, chunk_size=Config.CHUNK_SIZE, overlap=Config.CHUNK_OVERLAP)
        combined_context = "\n\n--- SECTION BREAK ---\n\n".join(chunks[:10])
        text_answer = ask_gemini_with_text(question, combined_context, model=Config.MODEL_FREE)
    
    # Step 4: If there are pages with images, also get visual answer
    image_answer = ""
    images_processed = 0
    
    if pages_needing_vision:
        images = []
        for page_num in pages_needing_vision:
            img_bytes = render_page_to_image(pdf_bytes, page_num, dpi=150)
            images.append(img_bytes)
            images_processed += 1
        
        if images:
            image_answer = ask_gemini_with_multiple_images(
                images, 
                f"Look at these pages from a textbook. {question}",
                thinking_level=Config.THINKING_LEVEL_PAID
            )
    
    # Step 5: Combine answers
    if text_answer and image_answer:
        combined = f"{text_answer}\n\n--- DIAGRAMS AND FIGURES ANALYSIS ---\n{image_answer}"
    elif image_answer:
        combined = image_answer
    else:
        combined = text_answer or "Could not process this PDF. It may be corrupted or password-protected."
    
    return {
        "answer": combined,
        "method_used": "hybrid_text_and_images" if pages_needing_vision else "text_only",
        "images_processed": images_processed,
        "pages_needing_vision": pages_needing_vision,
        "total_pages": metadata.get("page_count", 0),
        "processing_time": round(time.time() - start_time, 2)
    }


# ================================================================
# SMART ROUTER (CHOOSES BASED ON USER TIER)
# ================================================================

def process_pdf(pdf_bytes: bytes, question: str, tier: str = "free") -> Dict:
    """
    Main entry point - routes to appropriate processor based on user tier.
    
    tier: "free" or "paid"
    """
    if tier == "free":
        return process_pdf_free(pdf_bytes, question)
    else:
        return process_pdf_paid(pdf_bytes, question)


# ================================================================
# DIRECT QUESTION (NO PDF NEEDED)
# ================================================================

def ask_gemini_direct(question: str, tier: str = "free") -> Dict:
    """
    Answer a question directly without any PDF context.
    Works like a general AI assistant.
    
    Args:
        question: The user's question
        tier: "free" or "paid" (affects which model is used)
    
    Returns:
        Dictionary with answer and metadata
    """
    start_time = time.time()
    
    # Choose model based on tier
    if tier == "paid":
        model = Config.MODEL_PAID
        thinking_level = Config.THINKING_LEVEL_PAID
    else:
        model = Config.MODEL_FREE
        thinking_level = None
    
    # Simple prompt (no context)
    prompt = f"""You are Lurnic, a helpful AI study assistant.

Student's question: {question}

Please provide a clear, accurate, and educational answer. Be concise but thorough.
"""
    
    try:
        # Configure thinking level for paid tier
        config = {}
        if tier == "paid" and thinking_level:
            config["thinking_config"] = {"type": thinking_level}
        
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config if config else None
        )
        
        return {
            "answer": response.text,
            "method_used": "direct_ai",
            "images_processed": 0,
            "processing_time": round(time.time() - start_time, 2),
            "tier_used": tier
        }
    except Exception as e:
        return {
            "answer": f"Error: {str(e)}",
            "method_used": "error",
            "images_processed": 0,
            "processing_time": round(time.time() - start_time, 2),
            "tier_used": tier
        }


print("✓ core.py loaded successfully")