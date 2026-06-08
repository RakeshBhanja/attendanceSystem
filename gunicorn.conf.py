import os

# Bind to 0.0.0.0 on the port specified by Hugging Face (default 7860)
bind = f"0.0.0.0:{os.environ.get('PORT', '7860')}"

# Use 1 worker to save RAM on the free tier (16GB shared)
# face-recognition/dlib models consume significant memory per worker process
workers = 1

# Use multiple threads to handle concurrent web requests without blocking
threads = 4

# Increase timeout since face encoding computation can take a few seconds
timeout = 120

# Keepalive connections configuration
keepalive = 2
