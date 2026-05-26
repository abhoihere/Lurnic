# src/lurnic/__init__.py
"""
Lurnic - AI-powered textbook study assistant
"""

__version__ = "0.2.0"
__author__ = "Lurnic Developer"

from .core import process_pdf, process_pdf_free, process_pdf_paid
from .config import Config
from .api import app

__all__ = [
    "process_pdf",
    "process_pdf_free", 
    "process_pdf_paid",
    "Config",
    "app"
]

print("✓ Lurnic package loaded")
