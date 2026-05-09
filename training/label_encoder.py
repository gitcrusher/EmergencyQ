# training/label_encoder.py
# SRS Phase 2 Step 2.1 — Fit and save LabelEncoder for 5 SRS classes

import pandas as pd
import joblib
import os
from sklearn.preprocessing import LabelEncoder

TRAIN_CSV   = "dataset/processed/train.csv"
ENCODER_OUT = "backend/app/model/label_encoder.pkl"

os.makedirs(os.path.dirname(ENCODER_OUT), exist_ok=True)

df = pd.read_csv(TRAIN_CSV)

le = LabelEncoder()
le.fit(df["label"])

joblib.dump(le, ENCODER_OUT)

print("Label encoder saved to:", ENCODER_OUT)
print("Classes:", le.classes_.tolist())
# Expected: ['Accident', 'Fire', 'Flood', 'Medical', 'Other']
assert list(le.classes_) == ["Accident", "Fire", "Flood", "Medical", "Other"], \
    "Unexpected classes — check your dataset labels."
print(" Label encoder ready.")