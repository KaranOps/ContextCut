from fastapi import FastAPI
from app.api import endpoints
from app.core import config
import uvicorn

app = FastAPI(title="ContextCut API")

app.include_router(endpoints.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to ContextCut API"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
