# ContextCut


ContextCut is an AI-powered video editing tool that automatically synchronizes B-roll footage to your main A-roll video based on semantic context, creating a professional "AI Director" edit plan.

## Architecture
![Architecture Diagram](Architecture_ContextCut.png)


## Prerequisites

- **Python**: 3.10+ recommended
- **Node.js**: 16+
- **FFmpeg**: Must be installed and available in your system PATH (required for video processing).

## Setup & Installation

### Backend Setup

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # Windows
    python -m venv .venv
    .\.venv\Scripts\activate

    # Mac/Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the `backend` directory. You can copy the example below:

    ```ini
    # API Keys (Required)
    OPENAI_API_KEY=sk-...
    GROQ_API_KEY=gsk_...

    # Application Settings (Optional - Defaults shown)
    PROJECT_NAME="ContextCut"
    
    # Model Configuration
    WHISPER_MODEL_SIZE=small
    VISION_FRAME_INTERVAL=2
    
    # Editing Constraints
    MIN_BROLL_DURATION=1.5
    BROLL_COOL_DOWN_SECONDS=5.0
    MIN_LLM_CONFIDENCE=0.6
    
    # Vector Search
    EMBEDDING_PROVIDER=local
    CHROMA_DB_PATH=./chroma_db
    ```

### Frontend Setup

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

## Running the Application

 You need to run both the backend and frontend servers simultaneously.

### 1. Start the Backend API
In your **backend** terminal (with virtual environment activated):
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*The API will be accessible at [http://localhost:8000](http://localhost:8000)*

### 2. Start the Frontend UI
In your **frontend** terminal:
```bash
npm run dev
```
*The UI will be accessible at [http://localhost:5173](http://localhost:5173)*

## Usage Guide
1.  Open the web app.
2.  **A-Roll**: Upload your main narrative video.
3.  **B-Roll**: Upload a gallery of B-roll clips to be inserted.
4.  Click **"Generate Edit Plan"**.
5.  Wait for the AI to analyze the semantic context and visual content.
6.  View the generated timeline matching your B-roll to the spoken content.

## Testing

For developers, there are several test scripts available in the `backend/tests` directory to verify individual components and the full API pipeline.

### Unit Tests
These scripts verify specific services (Transcription, Vision, Timeline Logic) in isolation.

```bash
# Verify Audio Extraction & Transcription
python backend/tests/manual_audio_test.py
python backend/tests/manual_translation_test.py

# Verify Vision Processing (Scene description)
python backend/tests/manual_vision_test.py

# Verify Timeline Generation Logic (Mock data)
python backend/tests/manual_timeline_test.py
```

### Combined/Integration Test
The `test_api_server.py` script tests the full end-to-end flow by interacting with the running API server.

1.  **Ensure the Backend is running**:
    ```bash
    uvicorn app.main:app --reload
    ```
2.  **Edit the Test Script** (Optional):
    Open `backend/tests/test_api_server.py` and ensure the `BROLL_FILES` and `AROLL_FILE` paths point to valid video files on your machine.
3.  **Run the Test**:
    ```bash
    python backend/tests/test_api_server.py
    ```
    This will:
    - Check the API Health.
    - Upload B-roll videos.
    - Submit an A-roll video for processing.
    - Poll the status until the generated timeline is complete.

