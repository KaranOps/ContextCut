# ContextCut

## Project Structure

```
contextCut/
├── backend/
│   ├── app/
│   │   ├── api/                 # API Routes (The "Front Door")
│   │   │   ├── __init__.py
│   │   │   └── endpoints.py     # Handle file uploads & trigger generation
│   │   │
│   │   ├── core/                # Configuration
│   │   │   ├── __init__.py
│   │   │   └── config.py        # Env vars (OpenAI Keys, Paths)
│   │   │
│   │   ├── schemas/             # Pydantic Models (Data Contracts)
│   │   │   ├── __init__.py
│   │   │   └── timeline.py      # Defines the structure of the JSON Plan
│   │   │
│   │   ├── services/            # Business Logic (The "Brain")
│   │   │   ├── __init__.py
│   │   │   ├── audio_extractor.py # MoviePy/FFmpeg audio extraction
│   │   │   ├── transcriber.py     # OpenAI Whisper logic
│   │   │   ├── vision_encoder.py  # CLIP/BLIP logic (B-Roll analysis)
│   │   │   ├── director.py        # LLM Logic (Generates the JSON Plan)
│   │   │   └── renderer.py        # (Future) FFmpeg stitching logic
│   │   │
│   │   ├── utils/               # Helpers
│   │   │   ├── file_manager.py    # Saving uploads, cleaning temp files
│   │   │   └── logger.py          # Structured logging
│   │   │
│   │   └── main.py              # Application Entry Point
│   │
│   ├── tests/                   # Unit tests
│   ├── .env                     # Secrets
│   └── requirements.txt
│
├── frontend/                    # React App (Next.js or Vite)
│
├── data/                        # Local Storage (Simulating S3 bucket)
│   ├── uploads/                 # Raw A-roll/B-roll
│   ├── processed/               # Extracted frames/audio
│   └── outputs/                 # Final rendered videos
│
└── README.md
```