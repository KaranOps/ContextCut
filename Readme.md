# ContextCut

ContextCut is an AI-powered video editing tool that automatically synchronizes B-roll footage to your main A-roll video based on semantic context, creating a professional "AI Director" edit plan.

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
