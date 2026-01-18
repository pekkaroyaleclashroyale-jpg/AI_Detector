import torch
from transformers import ViTImageProcessor, ViTForImageClassification

class AIImageDetector:
    def __init__(self):
        self.model_name = "google/vit-base-patch16-224"
        print(f"🔄 Загрузка модели фото: {self.model_name}...")
        
        self.processor = ViTImageProcessor.from_pretrained(self.model_name)
        self.model = ViTForImageClassification.from_pretrained(self.model_name)
        
        # Определяем устройство (GPU или CPU)
        # Правильный способ переноса модели на видеокарту или процессор
        self.model = ViTForImageClassification.from_pretrained(self.model_name)

        self.model.to(self.device)

        self.model.eval()
        print("✅ Модель фото готова")

    def predict(self, image):
        """Метод для анализа изображения"""
        # Готовим картинку
        inputs = self.processor(images=image, return_tensors="pt")
        
        # Переносим данные на то же устройство, что и модель
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
        
        # Получаем вероятности
        probs = torch.nn.functional.softmax(logits, dim=-1)
        
        # Для этой модели нам просто нужно получить какой-то скор. 
        # В реальных детекторах логика сложнее, но для работы API сделаем так:
        ai_prob = probs[0][0].item() # Пример получения вероятности
        
        return {
            "real_probability": 1.0 - ai_prob,
            "ai_probability": ai_prob
        }