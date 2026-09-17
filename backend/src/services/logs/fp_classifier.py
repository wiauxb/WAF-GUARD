"""
Step 1: FP/TP classification using the local fine-tuned ModernBERT model.

Ported from false_positives_classification/api/services/fp_classifier.py.
"""
from pathlib import Path
from typing import List, Dict

import pandas as pd
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from .parser import parse_log_file, transform_entry
from .features import extract_features_from_entry
from .processor import format_log_text


def _to_native(v):
    """Convert numpy scalar types to plain Python types for JSON serialisation."""
    return v.item() if hasattr(v, "item") else v


class FPClassifier:
    """Loads the FP/TP model once and exposes a predict() method."""

    def __init__(self, model_dir: Path, device: str, max_seq_len: int = 2048) -> None:
        self.device = device
        self.max_seq_len = max_seq_len
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir).to(device)
        self.model.eval()

    def predict(self, log_file: Path, batch_size: int = 16) -> List[Dict]:
        """Parse a raw ModSecurity log file and return per-entry prediction dicts.

        Each dict contains:
            _parsed   : full transform_entry() output (sections A/B/C/F/H/I/J)
            _features : all 26 fields from extract_features_from_entry() (native Python types)
            _text     : formatted NL text (internal, used for step-2 attack classification)
            prediction, confidence, fp_probability, tp_probability
        """
        raw_entries = parse_log_file(log_file)
        if not raw_entries:
            return []

        transformed = [transform_entry(e) for e in raw_entries]
        features = [extract_features_from_entry(e) for e in transformed]
        df = pd.DataFrame(features)
        df["text"] = df.apply(format_log_text, axis=1)
        texts = df["text"].tolist()

        results: List[Dict] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            inputs = self.tokenizer(
                batch,
                truncation=True,
                padding=True,
                max_length=self.max_seq_len,
                return_tensors="pt",
            ).to(self.device)

            with torch.no_grad():
                logits = self.model(**inputs).logits

            probs = torch.softmax(logits, dim=-1).cpu().numpy()

            for j, prob in enumerate(probs):
                idx = i + j
                pred_label = int(prob.argmax())
                features_native = {k: _to_native(v) for k, v in features[idx].items()}

                results.append(
                    {
                        "_parsed": transformed[idx],
                        "_features": features_native,
                        "_text": texts[idx],
                        "prediction": "false_positive" if pred_label == 0 else "true_positive",
                        "confidence": float(prob.max()),
                        "fp_probability": float(prob[0]),
                        "tp_probability": float(prob[1]),
                    }
                )

        return results
