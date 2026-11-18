import io
import os
from PIL import Image, ImageDraw, ImageFont

def generate_matrix_image(matrix: dict[str, int], lang: str = "uk") -> bytes:
    """
    Накладає числа Матриці Долі на фон і повертає байти зображення у форматі PNG.
    """
    language = lang if lang in {"uk", "en", "ru"} else "uk"
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bg_path = os.path.join(base_dir, "assets", "karma", language, "matrix.jpg")
    font_path = os.path.join(base_dir, "assets", "fonts", "Montserrat-Bold.ttf")
    
    with Image.open(bg_path) as source:
        img = source.convert("RGB")
    draw = ImageDraw.Draw(img)
    
    font_size = 70
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        font = ImageFont.load_default()

    coords = {
        "portrait": (123, 633),
        "talent": (511, 224),
        "social": (898, 633),
        "karma": (511, 1033),
        "center": (511, 633),
    }

    # Світло-золотий колір для тексту (в стилі ліній макета)
    text_color = (255, 216, 139)

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
