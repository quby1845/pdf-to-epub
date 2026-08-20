# syntax=docker/dockerfile:1

ARG CUDA_IMAGE=nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04
FROM scratch AS syntax-check

FROM ${CUDA_IMAGE}

LABEL org.opencontainers.image.title="PDF to EPUB OCR" \
      org.opencontainers.image.description="Local GPU-accelerated OCR conversion from PDF to EPUB" \
      org.opencontainers.image.source="https://github.com/quby1845/pdf-to-epub" \
      org.opencontainers.image.licenses="MIT"

ARG DEBIAN_FRONTEND=noninteractive
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu126

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/pdf-to-epub-venv \
    XDG_CACHE_HOME=/cache
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        calibre \
        pandoc \
        poppler-utils \
        python3 \
        python3-venv \
        tini \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv "${VIRTUAL_ENV}" \
    && python -m pip install --upgrade pip \
    && python -m pip install torch torchvision --index-url "${TORCH_INDEX_URL}"

WORKDIR /opt/pdf-to-epub
COPY . .
RUN python -m pip install --no-cache-dir . \
    && useradd --create-home --uid 1000 --shell /usr/sbin/nologin app \
    && install -d --owner=app --group=app /cache /workspace/input /workspace/output

USER app
WORKDIR /workspace

VOLUME ["/cache", "/workspace/input", "/workspace/output"]
ENTRYPOINT ["/usr/bin/tini", "--", "pdf-to-epub-ocr"]
CMD []
