# LandStack API (Phase 14a). Build from the REPOSITORY ROOT:
#   docker build -f backend/Dockerfile -t landstack-api .
# Run (all settings come from environment variables; nothing secret is baked in):
#   docker run -p 8000:8000 -e DATABASE_URL=... -e JWT_SECRET=... landstack-api
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MPLCONFIGDIR=/tmp/matplotlib \
    NUMBA_CACHE_DIR=/tmp/numba

# libgomp1: the OpenMP runtime scikit-learn and SHAP use. Fonts: ReportLab draws the PDF with its built-in fonts plus the Noto
# Sans Devanagari files that are kept in backend/app/fonts (HarfBuzz shapes Hindi and Marathi with them), so no system fonts are needed.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. packages first (this layer is cached until requirements.txt changes)
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

# 2. the code
COPY backend backend
COPY db db
COPY ml ml
COPY chatbot chatbot

# 3. things that are NOT in git by design, built here:
#    - the "unusual plot" model (generated data, fixed seed: the same model every time; it never changes a score)
#    - the Land Guide pages. They are scraped politely from the public sources listed in chatbot/sources.json. If that fails for any
#      reason the build carries on and the Guide answers from the project's own glossary alone (it says "I don't know" for the rest).
RUN python -m ml.make_dataset && python -m ml.train_unusual
RUN python -m chatbot.build || (echo "Land Guide pages could not be fetched: continuing with the glossary only" && python -m chatbot.build --index-only)

# 4. run as a normal user, not root
RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app

EXPOSE 8000
# $PORT is set by the host (Render). FORWARDED_ALLOW_IPS stays 127.0.0.1 unless you know the proxy's address: the visitor's address is
# read by the app itself (TRUSTED_PROXY_HOPS, see docs/DEPLOY.md), because trusting "*" here would let a visitor forge it.
CMD ["sh", "-c", "exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips \"${FORWARDED_ALLOW_IPS:-127.0.0.1}\""]
