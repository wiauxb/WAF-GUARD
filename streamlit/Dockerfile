FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install streamlit pandas langchain websockets

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health
