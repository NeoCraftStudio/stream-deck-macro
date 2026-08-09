"""Generates the app icon: a keycap with a lightning bolt above it.
Run manually when the icon design needs to change: python tools/make_icon.py
Outputs assets/icon.ico (multi-res) and assets/icon.png (source, 512x512).
"""
import math
import os

from PIL import Image, ImageDraw

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
os.makedirs(OUT_DIR, exist_ok=True)

SIZE = 512
KEY_BG = (30, 33, 41, 255)
KEY_TOP = (52, 57, 70, 255)
KEY_BORDER = (18, 20, 26, 255)
BOLT_FILL = (255, 209, 0, 255)
BOLT_OUTLINE = (120, 80, 0, 255)


def rounded_rect(draw, box, radius, fill, outline=None, width=0):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def build():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ---- Keycap (bottom 62% of the canvas) ----
    key_top_y = SIZE * 0.40
    key_box = (SIZE * 0.10, key_top_y, SIZE * 0.90, SIZE * 0.94)
    rounded_rect(draw, key_box, radius=48, fill=KEY_BORDER)

    inset = 10
    base_box = (key_box[0] + inset, key_box[1] + inset, key_box[2] - inset, key_box[3] - inset)
    rounded_rect(draw, base_box, radius=40, fill=KEY_BG)

    # Raised top face, offset up slightly for a pressed-keycap look
    face_inset = 26
    face_box = (
        base_box[0] + face_inset, base_box[1] + face_inset - 8,
        base_box[2] - face_inset, base_box[3] - face_inset - 18,
    )
    rounded_rect(draw, face_box, radius=28, fill=KEY_TOP)

    # ---- Lightning bolt, centered above/on the keycap ----
    # Classic zigzag, drawn in a local 0..100 x 0..140 box then scaled/positioned.
    bolt_pts_local = [
        (62, 0), (18, 62), (46, 62), (34, 140),
        (86, 52), (56, 52), (62, 0),
    ]
    bolt_w, bolt_h = 100, 140
    scale = (SIZE * 0.5) / bolt_w
    offset_x = SIZE * 0.30
    offset_y = SIZE * 0.06
    bolt_pts = [(offset_x + x * scale, offset_y + y * scale) for x, y in bolt_pts_local]

    draw.polygon(bolt_pts, fill=BOLT_FILL, outline=BOLT_OUTLINE)
    # Thicken the outline (PIL's polygon outline is 1px regardless of width param pre-9.2)
    for i in range(len(bolt_pts)):
        p1 = bolt_pts[i]
        p2 = bolt_pts[(i + 1) % len(bolt_pts)]
        draw.line([p1, p2], fill=BOLT_OUTLINE, width=6, joint="curve")

    img.save(os.path.join(OUT_DIR, "icon.png"))

    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(os.path.join(OUT_DIR, "icon.ico"), sizes=ico_sizes)
    print(f"Wrote {OUT_DIR}/icon.png and icon.ico")


if __name__ == "__main__":
    build()
