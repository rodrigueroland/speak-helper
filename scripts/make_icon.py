"""生成 SpeakHelper 应用图标（多分辨率 .ico）。

设计：圆角方形蓝→靛渐变底 + 白色喇叭声波，沿用应用内品牌视觉（#3B82F6）。
用法：在 speak_helper 根目录执行
    uv run python scripts/make_icon.py
产物：speak_helper/icon.ico、icon_preview.png
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "icon.ico"
PREVIEW = ROOT / "icon_preview.png"

# 品牌渐变：顶部亮蓝 -> 底部靛蓝
TOP = (74, 144, 255)   # 偏亮的 #4A90FF
BOT = (61, 90, 241)    # 靛蓝 #3D5AF1
WHITE = (255, 255, 255, 255)

# Windows exe / 快捷方式常用尺寸（256 为 ICO 标准上限）
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _build_background(size: int) -> Image.Image:
    """圆角方形 + 垂直渐变 + 轻微高光。"""
    grad = Image.new("RGB", (1, size))
    for y in range(size):
        t = y / max(size - 1, 1)
        grad.putpixel(
            (0, y),
            (
                int(_lerp(TOP[0], BOT[0], t)),
                int(_lerp(TOP[1], BOT[1], t)),
                int(_lerp(TOP[2], BOT[2], t)),
            ),
        )
    grad = grad.resize((size, size))

    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    margin = int(size * 0.055)
    radius = int(size * 0.225)
    md.rounded_rectangle(
        [margin, margin, size - margin, size - margin], radius=radius, fill=255
    )

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    img.paste(grad, (0, 0), mask)

    hl = Image.new("L", (size, size), 0)
    hd = ImageDraw.Draw(hl)
    hd.ellipse(
        [int(size * 0.08), int(-size * 0.35), int(size * 0.92), int(size * 0.42)],
        fill=60,
    )
    hl = hl.filter(ImageFilter.GaussianBlur(size * 0.04))
    hl = Image.composite(hl, Image.new("L", (size, size), 0), mask)
    white_layer = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    img = Image.alpha_composite(
        img,
        Image.composite(
            white_layer, Image.new("RGBA", (size, size), (0, 0, 0, 0)), hl
        ),
    )
    return img


def _draw_glyph(img: Image.Image, *, small: bool = False) -> None:
    """白色喇叭 + 两道声波弧，几何取自应用内 SVG（24 单位坐标系）。"""
    size = img.width
    draw = ImageDraw.Draw(img)

    unit = size / 24.0
    scale = 0.60

    def P(x: float, y: float) -> tuple[float, float]:
        cx = cy = size / 2.0
        return (cx + (x - 11.0) * unit * scale, cy + (y - 12.0) * unit * scale)

    speaker = [(11, 5), (6, 9), (2, 9), (2, 15), (6, 15), (11, 19)]
    draw.polygon([P(*pt) for pt in speaker], fill=WHITE)

    lw = max(1, int(2.05 * unit * scale))
    if small:
        lw = max(2, lw)

    for r in (5.0, 10.0):
        bbox = [*P(12 - r, 12 - r), *P(12 + r, 12 + r)]
        draw.arc(bbox, start=-45, end=45, fill=WHITE, width=lw)
        if not small:
            for ang in (-45, 45):
                rad = math.radians(ang)
                ex = 12 + r * math.cos(rad)
                ey = 12 + r * math.sin(rad)
                cxp, cyp = P(ex, ey)
                draw.ellipse(
                    [cxp - lw / 2, cyp - lw / 2, cxp + lw / 2, cyp + lw / 2],
                    fill=WHITE,
                )


def _render_icon(target: int) -> Image.Image:
    """按目标尺寸渲染；小图标单独超采样，避免缩放发糊。"""
    small = target <= 32
    ss = target * 8 if small else target * 4
    img = _build_background(ss)
    _draw_glyph(img, small=small)
    out = img.resize((target, target), Image.LANCZOS)
    if small:
        out = out.filter(ImageFilter.UnsharpMask(radius=0.6, percent=140, threshold=2))
    return out


def main() -> None:
    frames = [_render_icon(s) for s in ICO_SIZES]

    # Pillow 保存 ICO 时必须以最大帧为主图，否则只会写入 16×16
    largest = frames[-1]
    largest.save(
        OUT,
        format="ICO",
        sizes=[(s, s) for s in ICO_SIZES],
        append_images=frames[:-1],
    )

    frames[-1].save(PREVIEW)
    print(f"已生成: {OUT} ({OUT.stat().st_size // 1024} KB, {len(ICO_SIZES)} 档尺寸)")
    print(f"预览图: {PREVIEW}")


if __name__ == "__main__":
    main()
