"""Gera os icones PWA do Guardiao Gamer (escudo de protecao).

Uso (precisa do Pillow instalado):
    python generate_icons.py

Saida: icon-192.png e icon-512.png (ao lado deste arquivo).
"""

import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(__file__)
BG = (15, 51, 40)        # #0f3328 (verde escuro do tema)
SHIELD = (255, 255, 255)
CHECK = (21, 127, 91)    # #157f5b (verde marca)


def make_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fundo arredondado
    radius = int(size * 0.22)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=BG)

    # Escudo (poligono): topo reto, base em ponta
    w = size
    shield = [
        (0.20 * w, 0.18 * w),
        (0.80 * w, 0.18 * w),
        (0.80 * w, 0.55 * w),
        (0.50 * w, 0.86 * w),
        (0.20 * w, 0.55 * w),
    ]
    draw.polygon(shield, fill=SHIELD)

    # Check de protecao dentro do escudo
    check = [
        (0.36 * w, 0.50 * w),
        (0.46 * w, 0.62 * w),
        (0.66 * w, 0.36 * w),
    ]
    draw.line(check, fill=CHECK, width=max(4, int(size * 0.06)), joint="curve")

    return img


def main():
    for size in (192, 512):
        icon = make_icon(size)
        out = os.path.join(HERE, f"icon-{size}.png")
        icon.save(out)
        print("Saved:", out, icon.size)


if __name__ == "__main__":
    main()
