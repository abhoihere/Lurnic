# test_hybrid.py
import os
from src.lurnic import process_pdf, Config

print("=" * 60)
print("LURNIC HYBRID TEST - FREE vs PAID TIER")
print("=" * 60)

# Get a PDF file
pdf_path = input("\nEnter path to a PDF file: ")

if not os.path.exists(pdf_path):
    print(f"File not found: {pdf_path}")
    exit(1)

with open(pdf_path, 'rb') as f:
    pdf_bytes = f.read()

question = input("Enter your question: ")

# Test FREE tier
print("\n" + "=" * 60)
print("FREE TIER (Text Only)")
print("=" * 60)
free_result = process_pdf(pdf_bytes, question, tier="free")
print(f"Method: {free_result['method_used']}")
print(f"Time: {free_result['processing_time']} seconds")
print(f"\nAnswer:\n{free_result['answer']}")

# Test PAID tier
print("\n" + "=" * 60)
print("PAID TIER (Text + Selective Images)")
print("=" * 60)
paid_result = process_pdf(pdf_bytes, question, tier="paid")
print(f"Method: {paid_result['method_used']}")
print(f"Images processed: {paid_result.get('images_processed', 0)}")
print(f"Time: {paid_result['processing_time']} seconds")
print(f"\nAnswer:\n{paid_result['answer']}")

print("\n✓ Test complete")