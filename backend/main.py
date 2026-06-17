from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import os

from backend.tools.case_memory import init_database
from backend.tools.image_diagnosis import analyze_crop_image
from backend.tools.customer_profile import load_customers
from backend.agent_graph import run_agro_graph


app = FastAPI(
    title="Agro-Mind API",
    description="AI-powered agricultural support assistant backend",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    customer_id: str
    message: str


@app.on_event("startup")
def startup_event():
    init_database()


@app.get("/")
def home():
    return {
        "message": "Agro-Mind backend is running",
        "status": "ok",
        "workflow": "LangGraph",
    }


@app.get("/customers")
def get_customers():
    return load_customers()


# ==========================================
# IMAGE DIAGNOSIS ENDPOINT
# ==========================================
@app.post("/diagnose")
async def diagnose(file: UploadFile = File(...)):
    temp_file_path = f"temp_{file.filename}"

    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        result = analyze_crop_image(temp_file_path)
        return result

    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


# ==========================================
# CHAT ENDPOINT USING LANGGRAPH
# ==========================================
@app.post("/chat")
def chat(request: ChatRequest):
    return run_agro_graph(
        customer_id=request.customer_id,
        message=request.message,
    )