import torch
from transformers import AutoImageProcessor, AutoModelForImageClassification
from PIL import Image
import torch.nn.functional as F
from datetime import datetime

class AIDetectorModel:
    def __init__(self) -> None:
        self.model_version = "v2.0-AutoLoad"
        # Используем эту же модель, но через универсальные инструменты
        self.model_name = "umm-maybe/AI-image-detector"
        
        print(f"🚀 Загрузка нейросети {self.model_name}...")
        try:
            # AutoImageProcessor и AutoModel сами подберут нужный конфиг (Swin/ViT)
            self.processor = AutoImageProcessor.from_pretrained(self.model_name)
            self.model = AutoModelForImageClassification.from_pretrained(self.model_name)
            self.model.eval()
            self.ready = True
            print("✅ Модель успешно загружена и готова!")
        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}")
            self.ready = False

    def predict(self, image: Image.Image):
        if not self.ready:
            return self.fallback(image, "Модель не была загружена")

        try:
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            inputs = self.processor(images=image, return_tensors="pt")
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits

            probs = F.softmax(logits, dim=-1)
            
            # Классы модели: 0 - AI, 1 - Real
            ai_prob = float(probs[0][0])
            real_prob = float(probs[0][1])

            return {
                'real_probability': real_prob,
                'ai_probability': ai_prob,
                'is_real': real_prob > 0.5,
                'confidence': max(ai_prob, real_prob),
                'width': image.width,
                'height': image.height,
                'image_size': f"{image.width}x{image.height}",
                'watermark': "Прошло проверку" if real_prob > 0.5 else "AI Генерация",
                'model_version': self.model_version
            }
        except Exception as e:
            print(f"❌ Ошибка при анализе: {e}")
            return self.fallback(image, str(e))

    def fallback(self, image, error_msg):
        return {
            'real_probability': 0.5, 'ai_probability': 0.5,
            'is_real': True, 'confidence': 0.0,
            'width': getattr(image, 'width', 0), 'height': getattr(image, 'height', 0),
            'image_size': "0x0", 'watermark': "Ошибка анализа",
            'model_version': 'fallback'
        }

ai_model = AIDetectorModel()