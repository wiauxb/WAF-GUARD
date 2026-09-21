"""
FP/TP classifier service.

Wraps the fine-tuned ModernBERT model in fp_model/ behind one endpoint, mirroring the
contract of the attack-type service (model_na):

  POST /predict  {"texts": [str, ...]}
  ->             {"predictions": [{"prediction", "confidence", "fp_probability",
                                   "tp_probability"}, ...]}

`texts` must already be formatted with the exact template the model was fine-tuned on
(backend/src/services/logs/processor.py::format_log_text). The service does not parse logs.
"""
import logging
import os
from contextlib import asynccontextmanager
from typing import List

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers import AutoModelForSequenceClassification, AutoTokenizer

logger = logging.getLogger("fp_classifier")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

MODEL_DIR = os.getenv("MODEL_DIR", "/app/fp_model")
# ModernBERT supports 8192. The model was fine-tuned at 2048; 512 truncates the
# Messages/payload evidence on long requests.
MAX_SEQ_LEN = int(os.getenv("MAX_SEQ_LEN", "2048"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "16"))
MAX_TEXTS_PER_REQUEST = int(os.getenv("MAX_TEXTS_PER_REQUEST", "512"))

state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Loading model from {MODEL_DIR} on {device}")
    state["device"] = device
    state["tokenizer"] = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR).to(device)
    model.eval()
    state["model"] = model
    logger.info("Model ready")
    yield
    state.clear()


app = FastAPI(title="FP/TP classifier", version="1.0.0", lifespan=lifespan)


class PredictRequest(BaseModel):
    texts: List[str] = Field(min_length=1)


class Prediction(BaseModel):
    prediction: str  # "false_positive" | "true_positive"
    confidence: float
    fp_probability: float
    tp_probability: float


class PredictResponse(BaseModel):
    predictions: List[Prediction]


@app.get("/health")
def health():
    return {"status": "ok" if "model" in state else "loading", "device": state.get("device")}


# Plain `def`: FastAPI runs it in a worker thread, so inference never blocks /health.
@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    if "model" not in state:
        raise HTTPException(status_code=503, detail="Model not loaded yet")
    if len(req.texts) > MAX_TEXTS_PER_REQUEST:
        raise HTTPException(
            status_code=413,
            detail=f"At most {MAX_TEXTS_PER_REQUEST} texts per request, got {len(req.texts)}",
        )

    tokenizer, model, device = state["tokenizer"], state["model"], state["device"]
    out: List[Prediction] = []

    for i in range(0, len(req.texts), BATCH_SIZE):
        batch = req.texts[i:i + BATCH_SIZE]
        inputs = tokenizer(
            batch, truncation=True, padding=True, max_length=MAX_SEQ_LEN, return_tensors="pt"
        ).to(device)
        with torch.inference_mode():
            probs = torch.softmax(model(**inputs).logits, dim=-1).cpu().numpy()

        for prob in probs:
            out.append(
                Prediction(
                    prediction="false_positive" if int(prob.argmax()) == 0 else "true_positive",
                    confidence=float(prob.max()),
                    fp_probability=float(prob[0]),
                    tp_probability=float(prob[1]),
                )
            )

    return PredictResponse(predictions=out)
