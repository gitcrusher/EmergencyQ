# training/tokenizer_setup.py
# SRS Phase 2 — Download and save DistilBERT tokenizer locally

from transformers import DistilBertTokenizer
import os

MODEL_NAME  = "distilbert-base-uncased"
OUTPUT_DIR  = "backend/app/model/trained_model"

os.makedirs(OUTPUT_DIR, exist_ok=True)

print(f"Downloading tokenizer: {MODEL_NAME}")
tokenizer = DistilBertTokenizer.from_pretrained(MODEL_NAME)
tokenizer.save_pretrained(OUTPUT_DIR)

print(f"   Tokenizer saved to: {OUTPUT_DIR}")
print(f"   Files: {os.listdir(OUTPUT_DIR)}")