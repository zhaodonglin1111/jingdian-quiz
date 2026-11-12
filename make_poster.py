# -*- coding: utf-8 -*-
"""
企业家经典智慧自测 · 分享海报生成器

用法：
    python make_poster.py <扫码跳转网址> [输出文件名]

例：
    python make_poster.py https://zhaodonglin1111.github.io/jingdian-quiz/
    python make_poster.py https://xxx.com/quiz/ 海报_正式版.png

换网址后重跑即可，二维码和海报同时重出。
"""
import sys
import os
import math
import random

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import qrcode

# ---------------- 基础配置 ----------------
W, H = 1080, 1920

PAPER      = (246, 241, 231)
PAPER_DARK = (233, 224, 208)
INK        = (35, 32, 28)
INK_2      = (87, 81, 74)
INK_3      = (140, 132, 120)
LINE       = (221, 211, 194)
SEAL       = (168, 69, 44)

C_YI  = (47, 111, 94)
C_DAO = (58, 86, 120)
C_XIN = (168, 69, 44)

FONT_SERIF   = "C:/Windows/Fonts/STSONG.TTF"
FONT_SERIF_B = "C:/Windows/Fonts/STSONG.TTF"
FONT_SANS    = "C:/Windows/Fonts/msyh.ttc"
FONT_SANS_B  = "C:/Windows/Fonts/msyhbd.ttc"
FONT_KAI     = "C:/Windows/Fonts/simkai.ttf"


def font(path, size, index=0):
    return ImageFont.truetype(path, size, index=index)


def text_w(draw, s, f, spacing=0):
    if not s:
        return 0
    if spacing == 0:
        return draw.textlength(s, font=f)
    w = 0
    for ch in s:
        w += draw.textlength(ch, font=f) + spacing
    return w - spacing


def draw_text_sp(draw, xy, s, f, fill, spacing=0, anchor_left=True):
    """带字间距的文字绘制，返回结束 x"""
    x, y = xy
    for ch in s:
        draw.text((x, y), ch, font=f, fill=fill)
        x += draw.textlength(ch, font=f) + spacing
    return x


def wrap_cn(draw, s, f, max_w, spacing=0):
    """中文按像素宽度断行"""
    lines, cur = [], ""
    for ch in s:
        trial = cur + ch
        if text_w(draw, trial, f, spacing) > max_w and cur:
            lines.append(cur)
            cur = ch
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def draw_centered(draw, cy, s, f, fill, spacing=0, cx=W // 2):
    w = text_w(draw, s, f, spacing)
    draw_text_sp(draw, (cx - w / 2, cy), s, f, fill, spacing)


def make_paper_bg():
    """宣纸底：暖白 + 噪点 + 角落光晕"""
    img = Image.new("RGB", (W, H), PAPER)
    px = img.load()
    rnd = random.Random(20261112)
    # 细噪点
    for y in range(0, H, 1):
        for x in range(0, W, 1):
            pass
    # 用 numpy 更快，但为免依赖，改用分块噪点
    noise = Image.effect_noise((W, H), 12).convert("L")
    noise = noise.filter(ImageFilter.GaussianBlur(0.6))
    img = Image.composite(img, img.point(lambda v: max(0, v - 7)), noise.point(lambda v: 255 if v > 128 else 0))

    # 角落光晕（朱砂 / 青绿）
    glow = Image.new("RGB", (W, H), PAPER)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([-420, -520, 520, 380], fill=(238, 226, 214))
    gd.ellipse([W - 480, H - 560, W + 460, H + 420], fill=(228, 233, 226))
    glow = glow.filter(ImageFilter.GaussianBlur(180))
    img = Image.blend(img, glow, 0.55)
    return img


def draw_seal(img, cx, cy, size, ch="易"):
    """朱砂印章"""
    d = ImageDraw.Draw(img)
    # 阴影
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    sd.rounded_rectangle([cx - size // 2, cy - size // 2 + 8, cx + size // 2, cy + size // 2 + 8],
                         radius=18, fill=(168, 69, 44, 70))
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    img.paste(Image.alpha_composite(img.convert("RGBA"), sh).convert("RGB"), (0, 0))

    d = ImageDraw.Draw(img)
    d.rounded_rectangle([cx - size // 2, cy - size // 2, cx + size // 2, cy + size // 2],
                        radius=18, fill=SEAL)
    f = font(FONT_SERIF, int(size * 0.56))
    bb = d.textbbox((0, 0), ch, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text((cx - tw / 2 - bb[0], cy - th / 2 - bb[1]), ch, font=f, fill=(255, 253, 248))


def rounded_card(img, box, radius, fill, border=None, shadow=True, shadow_alpha=46):
    x0, y0, x1, y1 = box
    if shadow:
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        sd.rounded_rectangle([x0 + 4, y0 + 14, x1 + 4, y1 + 18], radius=radius,
                             fill=(35, 32, 28, shadow_alpha))
        sh = sh.filter(ImageFilter.GaussianBlur(22))
        img.paste(Image.alpha_composite(img.convert("RGBA"), sh).convert("RGB"), (0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill,
                        outline=border, width=2 if border else 1)
    return d


def make_qr(url, target_px):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=20,
        border=0,
    )
    qr.add_data(url)
    qr.make(fit=True)
    m = qr.get_matrix()
    n = len(m)
    # 用整数倍像素绘制每个模块，避免 NEAREST 缩放造成模块宽度不均
    cell = max(1, target_px // n)
    size = cell * n
    img = Image.new("RGB", (size, size), (255, 255, 255))
    px = img.load()
    for y, row in enumerate(m):
        for x, v in enumerate(row):
            if v:
                for dy in range(cell):
                    for dx in range(cell):
                        px[x * cell + dx, y * cell + dy] = (0, 0, 0)
    return img, size


def build(url, out_path, brand="经典智慧研习", sub_brand="企业家经典智慧自测"):
    random.seed(20261112)
    img = make_paper_bg()
    d = ImageDraw.Draw(img)

    # ---------- 顶部品牌 ----------
    f_brand = font(FONT_SANS, 25)
    y = 96
    draw_centered(d, y, "J I N G   D I A N · 经 典 智 慧", f_brand, INK_2, spacing=1)

    # 品牌下的短横线
    d.line([(W // 2 - 46, y + 52), (W // 2 + 46, y + 52)], fill=LINE, width=2)

    # ---------- 印章 ----------
    draw_seal(img, W // 2, 258, 108, "经")

    # ---------- 主标题 ----------
    f_title = font(FONT_SERIF, 82)
    t1 = "此刻的你，"
    t2 = "更适合从哪一门入？"
    draw_centered(d, 372, t1, f_title, INK, spacing=3)
    draw_centered(d, 480, t2, f_title, INK, spacing=3)

    # ---------- 副标题 ----------
    f_sub = font(FONT_SERIF, 34)
    draw_centered(d, 606, "易经看势　道德经知止　阳明心学定心", f_sub, INK_2, spacing=1)

    # ---------- 三色维度条 ----------
    tags = [("易　经", "观　势", C_YI), ("道 德 经", "知　止", C_DAO), ("阳 明 心 学", "定　心", C_XIN)]
    tag_w, tag_h, gap = 268, 116, 32
    total_w = tag_w * 3 + gap * 2
    tx = (W - total_w) // 2
    ty = 700
    for i, (name, core, color) in enumerate(tags):
        x0 = tx + i * (tag_w + gap)
        d.rounded_rectangle([x0, ty, x0 + tag_w, ty + tag_h], radius=16,
                            fill=(255, 253, 248), outline=LINE, width=2)
        # 左侧色条
        d.rounded_rectangle([x0, ty, x0 + 7, ty + tag_h], radius=4, fill=color)
        f_n = font(FONT_SANS_B, 30)
        f_c = font(FONT_SERIF, 26)
        nw = text_w(d, name, f_n, 1)
        cw = text_w(d, core, f_c, 1)
        d.text((x0 + (tag_w - nw) / 2 + 3, ty + 20), name, font=f_n, fill=INK)
        d.text((x0 + (tag_w - cw) / 2, ty + 68), core, font=f_c, fill=color)

    # ---------- 分隔线 ----------
    d.line([(140, 892), (W - 140, 892)], fill=LINE, width=2)

    # ---------- 核心钩子文案 ----------
    f_hook = font(FONT_SERIF, 42)
    draw_centered(d, 940, "十个问题，看清当下先着力哪一层", f_hook, INK, spacing=2)

    f_hook2 = font(FONT_SERIF, 34)
    draw_centered(d, 1016, "局势 · 边界 · 本心，哪一处此刻更值得多花些心思？", f_hook2, INK_2, spacing=1)

    # ---------- 元信息 ----------
    f_meta = font(FONT_SANS, 27)
    meta = "10 道题　·　约 3 分钟　·　答完立即出结果"
    mw = text_w(d, meta, f_meta, 1)
    my = 1092
    d.rounded_rectangle([(W - mw) / 2 - 34, my - 12, (W + mw) / 2 + 34, my + 50],
                        radius=99, fill=(240, 233, 220))
    draw_centered(d, my, meta, f_meta, INK_2, spacing=1)

    # ---------- 二维码卡片 ----------
    card_w, card_h = 620, 640
    cx0 = (W - card_w) // 2
    cy0 = 1140
    rounded_card(img, (cx0, cy0, cx0 + card_w, cy0 + card_h), 26,
                 (255, 253, 248), border=LINE)

    d = ImageDraw.Draw(img)
    # 卡片顶部小字
    f_qr_top = font(FONT_SANS, 23)
    draw_centered(d, cy0 + 32, "微 信 扫 码 · 立 即 自 测", f_qr_top, INK_2, spacing=3, cx=W // 2)

    # 二维码（整数倍像素，避免缩放失真）
    qr_img, qr_px = make_qr(url, 400)
    qx = (W - qr_px) // 2
    qy = cy0 + 80
    # 二维码四周留白（静区），提升识别率
    quiet = 12
    d.rectangle([qx - quiet, qy - quiet, qx + qr_px + quiet, qy + qr_px + quiet], fill=(255, 255, 255))
    img.paste(qr_img, (qx, qy))

    # 二维码四角装饰
    d = ImageDraw.Draw(img)
    corner_len, corner_w = 26, 5
    pad = 16
    x0c, y0c, x1c, y1c = qx - pad, qy - pad, qx + qr_px + pad, qy + qr_px + pad
    for (px_, py_, dx_, dy_) in [(x0c, y0c, 1, 1), (x1c, y0c, -1, 1), (x0c, y1c, 1, -1), (x1c, y1c, -1, -1)]:
        d.line([(px_, py_), (px_ + corner_len * dx_, py_)], fill=SEAL, width=corner_w)
        d.line([(px_, py_), (px_, py_ + corner_len * dy_)], fill=SEAL, width=corner_w)

    # 二维码下说明
    f_qr_b = font(FONT_SANS_B, 30)
    draw_centered(d, cy0 + 510, "长按识别 · 或扫码作答", f_qr_b, INK, spacing=2)
    f_qr_b2 = font(FONT_SANS, 22)
    draw_centered(d, cy0 + 560, "答完自动生成你的经典学习方向", f_qr_b2, INK_2, spacing=1)

    # ---------- 底部 ----------
    d.line([(W // 2 - 60, 1838), (W // 2 + 60, 1838)], fill=LINE, width=2)
    f_foot = font(FONT_SANS, 23)
    draw_centered(d, 1862, sub_brand, f_foot, INK_2, spacing=3)

    # 淡淡的外框
    d.rectangle([26, 26, W - 27, H - 27], outline=(232, 223, 208), width=2)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    return out_path


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("错误：请传入扫码跳转网址")
        sys.exit(1)
    url = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "poster_分享海报.png"
    if not url.startswith(("http://", "https://")):
        print("警告：网址不是 http/https 开头，微信可能无法识别")
    p = build(url, out)
    print("已生成:", os.path.abspath(p))
    print("二维码内容:", url)


if __name__ == "__main__":
    main()