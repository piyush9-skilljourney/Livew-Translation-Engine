# BhashaCast: GCP Deployment Guide (Cloud Run)

This guide provides a step-by-step walkthrough for deploying the BhashaCast Live Translation Engine to Google Cloud Platform (GCP) using Cloud Run. It is based on the real-world challenges and fixes encountered during the initial production deployment.

---

## 📋 Prerequisites

Before you begin, ensure you have the following:

1.  **GCP Account & Project**:
    *   Create a project in the [GCP Console](https://console.cloud.google.com/).
    *   **Project ID**: Note your Project ID (e.g., `bhashacast-123456`).
    *   **Billing**: Ensure billing is enabled for your project. Google Cloud Run and Cloud Build require a linked billing account (even if you stay within the free tier).

2.  **Google Cloud CLI (gcloud)**:
    *   [Download and install](https://cloud.google.com/sdk/docs/install) the gcloud CLI.
    *   Initialize it: `gcloud init`.
    *   Set your project: `gcloud config set project [YOUR_PROJECT_ID]`.

3.  **Local Environment**:
    *   Node.js (for frontend build).
    *   Python 3.12 (for local testing).

---

## 🏗️ 1. Frontend Preparation

The frontend must be compiled into static assets before being served by the backend.

### A. Fix TypeScript Build Errors
Strict TypeScript checks may fail during `npm run build`. 
*   **Unused Imports**: Remove any unused icons or utilities from `App.tsx`.
*   **Buffer Type Casting**: If you encounter errors regarding `SharedArrayBuffer` vs `ArrayBuffer` in WebSocket `send()` calls, use `as any` casting:
    ```typescript
    socketRef.current.send(pcm16 as any);
    ```

### B. Build and Sync
1.  Navigate to the `frontend` directory:
    ```bash
    cd frontend
    npm run build
    ```
2.  Copy the compiled assets to the backend:
    ```powershell
    # Run from the project root
    xcopy /s /e /y frontend\dist backend\static\
    ```

---

## 🐍 2. Backend Preparation

### A. Dependency Management
Ensure `backend/requirements.txt` includes all runtime dependencies:
```text
fastapi
uvicorn[standard]
motor
python-dotenv
requests
python-multipart
pydantic
pydantic-settings
pymongo
certifi
cachetools
uvloop
sarvamai
httpx
```

### B. Package Structure
Ensure the `app` directory is treated as a package by adding an empty `__init__.py`:
```bash
touch backend/app/__init__.py
```

### C. Dockerfile Configuration
Use a lightweight Python image and ensure `ffmpeg` is installed:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p static
COPY . .
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

## 🚀 3. Deployment Steps

We recommend using the **Source-to-Service** deployment method, which handles container building automatically in the cloud.

### A. Enable Required APIs
Enable the necessary services in your project:
```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

### B. Configure IAM Permissions
Grant the default compute service account the necessary permissions to build and log:
```bash
# Get your project number from 'gcloud projects describe [PROJECT_ID]'
# Replace [PROJECT_NUMBER] below:
gcloud projects add-iam-policy-binding [PROJECT_ID] --member="serviceAccount:[PROJECT_NUMBER]-compute@developer.gserviceaccount.com" --role="roles/storage.objectViewer"
gcloud projects add-iam-policy-binding [PROJECT_ID] --member="serviceAccount:[PROJECT_NUMBER]-compute@developer.gserviceaccount.com" --role="roles/logging.logWriter"
gcloud projects add-iam-policy-binding [PROJECT_ID] --member="serviceAccount:[PROJECT_NUMBER]-compute@developer.gserviceaccount.com" --role="roles/artifactregistry.writer"
```

### C. Execute Deployment
Run the deployment from the `backend` directory. This command injects your secret API keys as environment variables:
```bash
cd backend
gcloud run deploy bhashacast \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "SARVAM_API_KEY=[YOUR_KEY],MONGODB_URL=[YOUR_MONGO_URL]"
```

---

## 🛠️ 4. Common Troubleshooting

| Issue | Cause | Fix |
| :--- | :--- | :--- |
| **404 Assets Not Found** | Static files mounted incorrectly. | In `main.py`, mount `StaticFiles` at the **root (`/`)** and ensure it is the **last** route defined. |
| **JSON Response at Root** | Conflicting `@app.get("/")` route. | Rename any health check or root route to `/api/health` to let React handle the homepage. |
| **ModuleNotFoundError** | Missing library in `requirements.txt`. | Add `cachetools`, `sarvamai`, or the missing lib to `requirements.txt` and redeploy. |
| **Forbidden (403)** | API or Billing not enabled. | Check the Logs URL provided in the terminal; enable the suggested API in the GCP Console. |
| **Container Port Error** | App not listening on port 8080. | Cloud Run expects port 8080 by default. Ensure `uvicorn` uses `--port 8080`. |

---

## 🌍 5. Live URL
Once successful, gcloud will provide a Service URL. 
Example: `https://bhashacast-123456.us-central1.run.app/`

Visit this URL to see your production-ready BhashaCast instance!
