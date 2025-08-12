import os
from PIL import Image, ImageOps

# ---------- 輔助：讀圖正規化（JPEG/透明/EXIF/色彩） ----------
def load_image_normalized(image_path: str, background=(255, 255, 255)) -> Image.Image:
    img = Image.open(image_path)
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, background)
        alpha = img.getchannel("A") if "A" in img.getbands() else None
        bg.paste(img.convert("RGB"), mask=alpha)
        img = bg
    elif img.mode == "P":
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, background)
        alpha = img.getchannel("A") if "A" in img.getbands() else None
        bg.paste(img.convert("RGB"), mask=alpha)
        img = bg
    elif img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    else:
        img = img.convert("RGB")
    return img

# ---------- 像素畫輸出----------
def convert_image_to_pixel_art(
    image_path: str,
    scale_factor: float = 0.1,
    output_path: str = "pixel_art.png",
    pixel_background=(255, 255, 255),
    jpeg_quality: int = 95,
    jpeg_progressive: bool = True,
    jpeg_optimize: bool = True,
    jpeg_subsampling: int = 0,  # 0=4:4:4，像素邊緣較銳利
):
    if scale_factor <= 0:
        raise ValueError("scale_factor 必須 > 0")

    img = load_image_normalized(image_path, background=pixel_background)
    ow, oh = img.size
    nw = max(1, int(round(ow * scale_factor)))
    nh = max(1, int(round(oh * scale_factor)))

    small = img.resize((nw, nh), Image.NEAREST)
    px_size_x = max(1, int(round(ow / nw)))
    px_size_y = max(1, int(round(oh / nh)))
    out_w, out_h = nw * px_size_x, nh * px_size_y

    out = Image.new("RGB", (out_w, out_h), color=pixel_background)
    sp = small.load()
    for y in range(nh):
        for x in range(nw):
            color = sp[x, y]
            block = Image.new("RGB", (px_size_x, px_size_y), color)
            out.paste(block, (x * px_size_x, y * px_size_y))

    ext = os.path.splitext(output_path)[1].lower()
    if ext in (".jpg", ".jpeg"):
        out.save(
            output_path,
            format="JPEG",
            quality=jpeg_quality,
            optimize=jpeg_optimize,
            progressive=jpeg_progressive,
            subsampling=jpeg_subsampling,
        )
    else:
        out.save(output_path)
    return output_path

# ---------- ASCII 共同邏輯 ----------
# 亮 → 暗（可自行微調字元表）
ASCII_CHARS_DEFAULT = " .'`^,:;Il!i><~+_-?][}{1)(|\\/*tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"

def to_luma(rgb):
    # 人眼感知加權（BT.709）
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def map_brightness_to_char(brightness, charset):
    idx = int(brightness / 255 * (len(charset) - 1))
    return charset[idx]

# ---------- 產生 ASCII（灰階） ----------
def image_to_ascii_grayscale(
    image_path: str,
    out_txt: str = "ascii_grayscale.txt",
    target_width: int = 120,
    char_aspect: float = 0.5,   # 字元寬高比修正：常見等寬字體約 0.5
    charset: str = ASCII_CHARS_DEFAULT,
):
    """
    target_width：輸出文字寬度（字元數）
    char_aspect：寬/高 校正；0.5 表示字元高度約為寬的 2 倍
    """
    img = load_image_normalized(image_path)
    ow, oh = img.size

    # 根據終端字元比例計算目標高度
    scale = target_width / ow
    target_height = max(1, int(round(oh * scale * char_aspect)))

    # 先縮到文字解像度
    small = img.resize((target_width, target_height), Image.BILINEAR).convert("RGB")
    sp = small.load()

    lines = []
    for y in range(target_height):
        row_chars = []
        for x in range(target_width):
            lum = to_luma(sp[x, y])
            ch = map_brightness_to_char(lum, charset)
            row_chars.append(ch)
        lines.append("".join(row_chars))

    text = "\n".join(lines)
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(text)
    return out_txt

# ---------- 產生 ASCII（ANSI 彩色真彩） ----------
def rgb_to_ansi_fg(r, g, b):
    return f"\x1b[38;2;{r};{g};{b}m"

def ansi_reset():
    return "\x1b[0m"

def image_to_ascii_ansi(
    image_path: str,
    out_txt: str = "ascii_ansi.txt",
    target_width: int = 120,
    char_aspect: float = 0.5,
    charset: str = ASCII_CHARS_DEFAULT,
    use_truecolor: bool = True,  # True=24bit；False可改成 256 色碼（如需）
):
    img = load_image_normalized(image_path)
    ow, oh = img.size
    scale = target_width / ow
    target_height = max(1, int(round(oh * scale * char_aspect)))

    small = img.resize((target_width, target_height), Image.BILINEAR).convert("RGB")
    sp = small.load()

    parts = []
    for y in range(target_height):
        line = []
        for x in range(target_width):
            r, g, b = sp[x, y]
            lum = to_luma((r, g, b))
            ch = map_brightness_to_char(lum, charset)
            if use_truecolor:
                line.append(f"{rgb_to_ansi_fg(r,g,b)}{ch}")
            else:
                # 簡易退化：直接真彩也行，或自行實作 256 色量化
                line.append(f"{rgb_to_ansi_fg(r,g,b)}{ch}")
        parts.append("".join(line) + ansi_reset())
    colored = "\n".join(parts)

    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(colored)
    return out_txt

# ---------- 範例執行 ----------
if __name__ == "__main__":
    file_name = "lucy.png"
    name_only,_ = os.path.splitext(file_name)
    # 1) 像素畫輸出
    convert_image_to_pixel_art(
        file_name,
        scale_factor=0.12,
        output_path=f"{name_only}_pixel_art.jpg",
        pixel_background=(255, 255, 255),
        jpeg_quality=95,
        jpeg_progressive=True,
        jpeg_optimize=True,
        jpeg_subsampling=0,
    )

    # 2) ASCII 灰階
    image_to_ascii_grayscale(
        file_name,
        out_txt=f"{name_only}_ascii_grayscale.txt",
        target_width=120,
        char_aspect=0.5,
        charset=ASCII_CHARS_DEFAULT,
    )

    # 3) ASCII ANSI 彩色（真彩）
    image_to_ascii_ansi(
        file_name,
        out_txt=f"{name_only}_ascii_ansi.txt",
        target_width=120,
        char_aspect=0.5,
        charset=ASCII_CHARS_DEFAULT,
        use_truecolor=True,
    )