FROM python:3.12-slim

WORKDIR /app

# CPU-only torch: the default wheel drags in ~2 GB of CUDA libraries this service does
# not use on a CPU host.
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt

# Weights are baked into the image so it runs anywhere with `docker run`. They are not in
# git: place them in fp_classifier/fp_model/ before building (see README).
COPY fp_model /app/fp_model
COPY src/main.py /app/main.py

ENV MODEL_DIR=/app/fp_model \
    MAX_SEQ_LEN=2048 \
    BATCH_SIZE=16

EXPOSE 8103
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8103"]
