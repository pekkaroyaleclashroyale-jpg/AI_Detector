import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch.nn.functional as F
import logging

# Настройка логирования, чтобы видеть ошибки в консоли
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AITextDetector:
    def __init__(self):
        self.model_name = "Hello-SimpleAI/chatgpt-detector-roberta"
        self.is_loaded = False
        
        logger.info(f"🔄 Загрузка модели: {self.model_name}...")
        try:
            # Выбор устройства: GPU (cuda), Apple Silicon (mps) или CPU
            if torch.cuda.is_available():
                self.device = torch.device("cuda")
            elif torch.backends.mps.is_available():
                self.device = torch.device("mps") # Для Mac M1/M2
            else:
                self.device = torch.device("cpu")
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            
            self.model.to(self.device)
            self.model.eval()
            
            logger.info(f"✅ Модель загружена на устройстве: {self.device}")
            self.is_loaded = True
        except Exception as e:
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА ЗАГРУЗКИ: {e}")
            self.is_loaded = False

    def predict(self, text):
        if not self.is_loaded:
            return "Ошибка: Модель не загружена", 0.0

        # Проверка на тип данных
        if not isinstance(text, str):
            return "Ошибка: Прислан не текст", 0.0

        if len(text.strip()) < 10:
            return "Текст слишком короткий (нужно > 10 символов)", 0.0

        try:
            # Токенизация
            inputs = self.tokenizer(
                text, 
                return_tensors="pt", 
                truncation=True, 
                max_length=512
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
            
            # Получение вероятностей
            probabilities = F.softmax(logits, dim=-1)
            
            # В этой модели индекс 1 - это AI, индекс 0 - Human
            ai_probability = probabilities[0][1].item() * 100
            
            # Формируем вердикт
            if ai_probability > 80:
                verdict = "🤖 Это точно ИИ"
            elif ai_probability > 50:
                verdict = "🤖 Скорее всего ИИ"
            else:
                verdict = "👤 Текст написал человек"
                
            return verdict, round(ai_probability, 1)

        except Exception as e:
            logger.error(f"Ошибка анализа текста: {e}")
            return "Ошибка при обработке", 0.0