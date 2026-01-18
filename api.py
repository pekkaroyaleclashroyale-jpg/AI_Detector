from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from PIL import Image
import io

app = FastAPI()

@app.get("/")
def root():
    return {"message": "API работает"}

@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"): # type: ignore
        return JSONResponse(status_code=400, content={"error": "Только JPG или PNG"})

    image_bytes = await file.read()

    try:
        image = Image.open(io.BytesIO(image_bytes))
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Не изображение"})

    return {
        "ai_probability": 0.75,
        "verdict": "Скорее всего ИИ"
    }
