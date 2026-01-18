from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PIL import Image
import io
import os
import base64
import json
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
from pathlib import Path
import uvicorn

try:
    from utils.watermark import add_watermark
except ImportError:
    from utils.watermark import add_watermark
from model import ai_model 
from text_model import AITextDetector

# 1. Инициализация приложения
app = FastAPI(title="AI Detector Hub")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Разрешает запросы со всех устройств
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
text_detector = AITextDetector()

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = BASE_DIR / "uploads"
LOG_FILE = UPLOAD_DIR / "detections.json"

for folder in [TEMPLATES_DIR, STATIC_DIR, UPLOAD_DIR]:
    folder.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

class TextRequest(BaseModel):
    text: str

def log_detection(data: dict):
    logs = []
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except:
            logs = []
    data["timestamp"] = datetime.now().isoformat()
    logs.append(data)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")

        result = ai_model.predict(image)
        
        # Русский текст для водяного знака
        is_real = result["real_probability"] >= 0.5
        watermark_text = "Прошел проверку на AI)" if is_real else "Не прошел проверку на AI!"

        # ВАЖНО: передаем 'image', а не 'img'
        image_with_wm = add_watermark(image, watermark_text)

        img_io = io.BytesIO()
        image_with_wm.save(img_io, format="JPEG", quality=95)
        img_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')

        response_data = {
            "type": "image",
            "success": True,
            "real_probability": float(result["real_probability"]),
            "ai_probability": float(result["ai_probability"]),
            "watermark": watermark_text,
            "image_base64": img_base64
        }
        
        log_detection(response_data)
        return response_data
    except Exception as e:
        print(f"❌ Ошибка фото: {e}")
        raise HTTPException(500, detail=str(e))

@app.post("/detect-text")
async def detect_text(data: TextRequest):
    try:
        verdict, score_percent = text_detector.predict(data.text)
        response_data = {
            "type": "text",
            "success": True,
            "ai_score": score_percent,
            "label": verdict
        }
        log_detection(response_data)
        return response_data
    except Exception as e:
        print(f"❌ Ошибка текста: {e}")
        return {"success": False, "ai_score": 0.0, "label": "Ошибка"}

@app.get("/health")
async def health():
    return {"status": "online", "time": datetime.now().isoformat()}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)