"""
Gera os ícones PNG do EasyTracker para uso no PWA (tela inicial do iPhone).

Execute uma vez, a partir de src/:
    python generate_icons.py

Requer Pillow (já está no requirements.txt / venv).
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZES = [192, 512]
STATIC = Path(__file__).parent / "static"
STATIC.mkdir(exist_ok=True)

# Cores do design system do app
BG_COLOR = (61, 214, 140)  # --accent  #3dd68c
TEXT_COLOR = (12, 17, 24)  # --bg      #0c1118

FONT_CANDIDATES = [
    "/System/Library/Fonts/Helvetica.ttc",  # macOS
    "/System/Library/Fonts/SFCompact.ttf",  # macOS alternativo
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
]


def _best_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


for px in SIZES:
    img = Image.new("RGB", (px, px), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font = _best_font(px // 3)
    text = "ET"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (px - text_w) / 2 - bbox[0]
    y = (px - text_h) / 2 - bbox[1]

    draw.text((x, y), text, fill=TEXT_COLOR, font=font)

    dest = STATIC / f"icon-{px}.png"
    img.save(dest, "PNG")
    print(f"✓ {dest}")

print("Ícones gerados com sucesso.")
