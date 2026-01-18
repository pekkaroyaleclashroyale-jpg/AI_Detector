from PIL import Image, ImageDraw, ImageFont, ImageOps
import os

def add_watermark(image: Image.Image, text: str) -> Image.Image:
    # 1. Подготовка основы
    img = image.copy().convert("RGBA")
    width, height = img.size
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    font_size = max(20, width // 30)
    
    # 2. Загрузка шрифта
    font = None
    font_paths = ["arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:\\Windows\\Fonts\\arial.ttf"]
    for path in font_paths:
        try:
            font = ImageFont.truetype(path, size=font_size)
            break
        except: continue
    if not font: font = ImageFont.load_default()

    # 3. Работа с лицом (аватаркой)
    # Путь к файлу с лицом (положи файл face.png рядом с main.py или укажи полный путь)
    face_path = "face.png" 
    face_img = None
    
    if os.path.exists(face_path):
        try:
            face_img = Image.open(face_path).convert("RGBA")
            # Размер лица пропорционально тексту
            face_size = font_size + 20
            face_img = face_img.resize((face_size, face_size), Image.Resampling.LANCZOS)
            
            # Делаем лицо круглым
            mask = Image.new("L", (face_size, face_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, face_size, face_size), fill=255)
            
            circular_face = Image.new("RGBA", (face_size, face_size), (0, 0, 0, 0))
            circular_face.paste(face_img, (0, 0), mask=mask)
            face_img = circular_face
        except Exception as e:
            print(f"Ошибка загрузки лица: {e}")

    # 4. Расчет позиций
    padding = 20
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Координаты текста (справа внизу)
    x_text = width - text_width - padding
    y_text = height - text_height - padding

    # 5. Наложение элементов
    if face_img:
        # Позиция лица слева от текста
        face_x = int(x_text - face_img.width - 15)
        face_y = int(y_text - (face_img.height // 4))
        overlay.paste(face_img, (face_x, face_y), face_img)

    # Рисуем текст (с тенью для читаемости)
    draw.text((x_text + 1, y_text + 1), text, fill=(0, 0, 0, 180), font=font)
    draw.text((x_text, y_text), text, fill=(255, 255, 255, 220), font=font)

    return Image.alpha_composite(img, overlay).convert("RGB")