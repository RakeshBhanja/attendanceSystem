# Use official Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7860 \
    HOME=/home/user

# Install system dependencies needed to compile dlib and run OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    g++ \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Set up a new user named "user" with UID 1000 (Hugging Face Spaces requirement)
RUN useradd -m -u 1000 user

# Set up working directory
WORKDIR $HOME/app

# Copy requirements file first to leverage Docker caching
COPY --chown=user:user requirements.txt .

# Install dependencies as the non-root user
USER user
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy the rest of the application files with proper ownership
COPY --chown=user:user . .

# Add local bin to PATH so installed commands are available
ENV PATH=$HOME/.local/bin:$PATH

# Expose port 7860
EXPOSE 7860

# Run the Flask app with Gunicorn
CMD ["gunicorn", "-c", "gunicorn.conf.py", "main:app"]
