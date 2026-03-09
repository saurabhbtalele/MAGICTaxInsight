FROM python:3.10-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies required for OCR, image processing, and Docling
# Includes --no-install-recommends for image size optimization
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    libmagic1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first to leverage Docker cache
COPY requirements.txt .
# Use CPU-only index for PyTorch to save ~800MB of unnecessary CUDA drivers
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

# ---------------------------------------------------------------------------
# PRE-DOWNLOAD ALL AI MODELS (while still root)
# Docker containers are ephemeral — models downloaded at runtime are lost.
# We bake everything into the image so extraction works instantly.
# ---------------------------------------------------------------------------

# Persistent model cache directory (will be owned by appuser below)
ENV HF_HOME=/opt/models/huggingface
ENV DOCLING_MODELS_PATH=/opt/models/docling

RUN mkdir -p /opt/models/huggingface /opt/models/docling

# 1) RapidOCR models (~50 MB from modelscope.cn → site-packages/rapidocr/models/)
RUN python -c "from rapidocr import RapidOCR; print('[build] Downloading RapidOCR models...'); RapidOCR(); print('[build] RapidOCR models OK')" \
    && chmod -R a+rw /usr/local/lib/python3.10/site-packages/rapidocr/

# 2) Docling models — DocLayNet + TableFormer (~700 MB from HuggingFace)
#    Initialising a DocumentConverter triggers the HF model download.
RUN python -c "import os; os.environ['HF_HOME']='/opt/models/huggingface'; print('[build] Downloading Docling models...'); from docling.document_converter import DocumentConverter; DocumentConverter(); print('[build] Docling models OK')"

# Create a non-root user (Security best practice)
RUN useradd -m -u 1000 appuser

# Give appuser ownership of the model cache
RUN chown -R appuser:appuser /opt/models

WORKDIR /app

# Copy the application source code with non-root ownership
COPY --chown=appuser:appuser . .

# Ensure output directory exists for volume mounting
RUN mkdir -p /app/output && chown appuser:appuser /app/output

# Switch to non-root user
USER appuser

# Use entrypoint syntax to allow passing arguments directly
ENTRYPOINT ["python", "tax_poc.py"]

# Provide a default argument (shows help text)
CMD ["--help"]

