import io
import os
from PIL import Image, ImageDraw, ImageFont

def generate_matrix_image(matrix: dict[str, int], lang: str = "uk") -> bytes:
    """
    Накладає числа Матриці Долі на фон і повертає байти зображення у форматі PNG.
    """
    bg_map = {
        "uk": "ua.png",
        "en": "en.png",
        "ru": "ru.png"
    }
    bg_filename = bg_map.get(lang, "ua.png")
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bg_path = os.path.join(base_dir, "assets", "matrix", bg_filename)
    font_path = os.path.join(base_dir, "assets", "fonts", "Montserrat-Bold.ttf")
    
    img = Image.open(bg_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    
    # 70 looks good for ~100px circles
    font_size = 70
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        font = ImageFont.load_default()

    coords = {
        "portrait": (180, 672),
        "talent": (560, 253),
        "social": (940, 672),
        "karma": (560, 1076),
        "center": (560, 672)
    }

    # Світло-золотий колір для тексту (в стилі ліній макета)
    text_color = (235, 195, 100, 255) 

    for key, (cx, cy) in coords.items():
        if key in matrix:
            text = str(matrix[key])
            draw.text((cx, cy), text, font=font, fill=text_color, anchor="mm")

    out_bio = io.BytesIO()
    img.save(out_bio, format="PNG")
    out_bio.seek(0)
    return out_bio.getvalue()

if __name__ == "__main__":
    # Test script
    test_matrix = {"portrait": 7, "talent": 12, "social": 21, "karma": 4, "center": 22}
    img_bytes = generate_matrix_image(test_matrix, "uk")
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_out.png")
    with open(out_path, "wb") as f:
        f.write(img_bytes)
    print("Saved to", out_path)
