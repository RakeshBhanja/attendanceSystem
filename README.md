# Face Recognition Attendance System (Hugging Face Spaces Deployment)

This repository is optimized for deployment to **Hugging Face Spaces** using the **Docker SDK**. It features a modern, responsive, dark-themed glassmorphic web dashboard that captures webcam feeds from the browser and runs real-time student face recognition at the backend.

---

## Folder Structure

Your project should be structured as follows:

```text
├── .gitignore                      # Git exclusion rules
├── Dockerfile                      # Production Docker container definition
├── README.md                       # Deployment and developer guide
├── attendance_core.py              # Face recognition processing core (dlib/OpenCV)
├── attendance_logs/                # (Auto-created) Logged attendance spreadsheets
├── gunicorn.conf.py                # Production Gunicorn server config
├── haarcascade_frontalface_default.xml # Face detection helper model
├── known_faces/                    # Saved student reference photos (e.g., "101.jpg", "102.png")
│   ├── 1.jpg
│   └── 2.jpg
├── main.py                         # Flask web application entrypoint
├── main_kivy.py                    # Original local desktop GUI Kivy application backup
├── requirements.txt                # Pinned python libraries
├── students_master.xlsx            # Master registration spreadsheet template
└── uploads/                        # (Auto-created) Folder for uploaded excel files
```

---

## Deployment to Hugging Face Spaces

### Step 1: Create a Space on Hugging Face
1. Navigate to [Hugging Face Spaces](https://huggingface.co/spaces) and log in.
2. Click **Create new Space**.
3. Choose a name for your Space (e.g., `attendance-system`).
4. Select **Docker** as the SDK.
5. Select the **Blank** template (or choose a base image, but using our custom Dockerfile is recommended).
6. Set the Space visibility to **Public** or **Private** as desired.
7. Click **Create Space**.

### Step 2: Configure Git Remote and Push Code
Run the following commands in your local repository terminal:

```bash
# 1. Add the Hugging Face Space as a git remote (replace username and space name)
git remote add hf https://huggingface.co/spaces/YOUR_HF_USERNAME/YOUR_SPACE_NAME

# 2. Add files and make a commit
git add .
git commit -m "Deploy face recognition attendance system to HF Spaces"

# 3. Push to Hugging Face
git push hf main
```

*(Note: Hugging Face might ask you for your Hugging Face username and your **git token** as password. You can generate a Git Write Access Token in your Hugging Face profile settings under Access Tokens.)*

---

## Local Verification & Testing

Before pushing to Hugging Face Spaces, you can test the Docker setup locally:

```bash
# 1. Build the Docker image
docker build -t attendance-app .

# 2. Run the Docker container locally (binding to port 7860)
docker run -p 7860:7860 attendance-app
```

Then visit `http://localhost:7860` in your web browser.

---

## Troubleshooting Guide

### 1. Slow Build Times (Dlib Compilation)
- **Problem**: `pip install dlib` or `pip install face-recognition` takes a very long time during the Docker build.
- **Why**: `dlib` is a C++ library and is compiled from source during the pip installation phase.
- **Fix**: The Dockerfile copies `requirements.txt` and runs `pip install` *before* copying the application code. This ensures Docker caches the heavy dlib compilation step. Subsequent builds will complete in seconds unless you modify `requirements.txt`.

### 2. Out of Memory (OOM) / Crashes on Hugging Face Spaces
- **Problem**: The space builds successfully but crashes during start-up or during scanning with an "OOM" or "Exit code 137" error.
- **Why**: `face-recognition` loads deep learning models, and multiple Gunicorn workers will multiply this memory footprint (each worker spawns its own python process loading the models).
- **Fix**: Our `gunicorn.conf.py` pins the number of workers to `1` and uses `4` threads. This shares the memory footprint among threads and prevents memory exhaustion. Do not increase `workers` beyond 1 on free tiers.

### 3. Webcam Access Denied / Black Screen
- **Problem**: The webcam preview is black, or browser alerts show "Permission Denied".
- **Why**: Web browsers block camera access (`getUserMedia`) on insecure origins. The site *must* be served over HTTPS.
- **Fix**: Hugging Face Spaces serves apps over secure `https://` by default, so it will work seamlessly. For local testing, use `localhost` (which browsers treat as secure by default) instead of your local IP address.

### 4. OpenCV Runtime Errors
- **Problem**: `ImportError: libGL.so.1: cannot open shared object file` or similar.
- **Why**: Standard OpenCV (`opencv-python`) requires X11/GUI display libraries, which are missing on headless servers like Docker.
- **Fix**: We use `opencv-python-headless` in `requirements.txt`. Additionally, the Dockerfile runs `apt-get install` to install essential graphics helper libraries (`libgl1-mesa-glx`, `libglib2.0-0`, etc.) to prevent runtime crashes.
