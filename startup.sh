#!/bin/bash
# CafeMate startup script for Azure App Service
# Tries uv first, falls back to pip + uvicorn

if command -v uv &> /dev/null; then
    uv run uvicorn main:app --host 0.0.0.0 --port 8000
else
    pip install -r requirements.txt
    uvicorn main:app --host 0.0.0.0 --port 8000
fi
