# src/lurnic/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Central configuration for Lurnic"""
    
    # API Key
    GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    
    # ================================================================
    # MODEL SELECTION (YOUR HYBRID ARCHITECTURE)
    # ================================================================
    
    # Free tier: Gemini 2.5 Flash-Lite (text only - $0.075/$0.30 per 1M tokens)
    MODEL_FREE = "gemini-2.5-flash-lite"
    
    # Paid tier: Gemini 3.1 Flash-Lite (multimodal - $0.25/$1.50 per 1M tokens)
    MODEL_PAID = "gemini-3.1-flash-lite"
    
    # Default model (use free for testing)
    MODEL_DEFAULT = MODEL_FREE
    
    # Thinking level for Gemini 3.1 Flash-Lite (paid tier)
    # Options: "minimal", "low", "medium", "high"
    THINKING_LEVEL_PAID = "medium"  # Good balance for diagram understanding
    
    # ================================================================
    # PDF PROCESSING SETTINGS
    # ================================================================
    
    CHUNK_SIZE = 5000           # Characters per chunk (text extraction)
    CHUNK_OVERLAP = 500         # Overlap between chunks
    MAX_PAGES = 1000
    MAX_FILE_SIZE_MB = 50
    MAX_IMAGE_PAGES_PER_REQUEST = 15  # Limit image pages to control cost
    
    # ================================================================
    # API SETTINGS
    # ================================================================
    
    REQUEST_TIMEOUT = 120
    MAX_RETRIES = 3

# Validate API key
if not Config.GEMINI_API_KEY:
    raise ValueError(
        "ERROR: GEMINI_API_KEY or GOOGLE_API_KEY not found in .env file.\n"
        "Please create a .env file with: GOOGLE_API_KEY=your_key_here"
    )

print("✓ Config loaded successfully")