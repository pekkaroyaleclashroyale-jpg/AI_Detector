from model import ai_model
from PIL import Image

# Создаем тестовое изображение
test_img = Image.new('RGB', (800, 600), color='blue')
result = ai_model.predict(test_img)

print("Тест модели:")
print(f"  Реальное: {result['real_probability']:.2%}")
print(f"  AI: {result['ai_probability']:.2%}")
print(f"  Результат: {'РЕАЛЬНОЕ' if result['is_real'] else 'AI'}")
