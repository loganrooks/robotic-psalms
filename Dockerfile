# Robotic Psalms - Ethereal computerized vocal arrangements
# Multi-stage build for smaller final image

FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies first (for caching)
WORKDIR /app
COPY pyproject.toml poetry.lock* ./

# Install pip and poetry, then export to requirements
RUN pip install --upgrade pip wheel setuptools

# Copy source and install
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY examples/ ./examples/
COPY README.md ./

# Install the package (non-editable for production)
RUN pip install ".[dev]"

# Download NLTK data during build (avoids runtime downloads)
RUN python -c "import nltk; nltk.download('averaged_perceptron_tagger', download_dir='/opt/nltk_data'); nltk.download('cmudict', download_dir='/opt/nltk_data')"

# ============================================
# Final runtime image
# ============================================
FROM python:3.11-slim AS runtime

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    espeak-ng \
    libespeak-ng1 \
    portaudio19-dev \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
ARG UID=1000
ARG GID=1000
RUN groupadd -g ${GID} psalms && \
    useradd -m -u ${UID} -g psalms psalms

# Copy virtual environment from builder (includes installed package)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy NLTK data from builder
COPY --from=builder /opt/nltk_data /opt/nltk_data
ENV NLTK_DATA="/opt/nltk_data"

# Copy application files (for examples and reference)
WORKDIR /app
COPY --from=builder /app/examples ./examples
COPY --from=builder /app/README.md ./

# Create output directory with correct ownership
RUN mkdir -p /app/output /app/input && \
    chown -R psalms:psalms /app

# Verify espeak-ng is working
RUN espeak-ng --version

# Switch to non-root user
USER psalms

# Set default command
ENTRYPOINT ["robotic-psalms"]
CMD ["--help"]
