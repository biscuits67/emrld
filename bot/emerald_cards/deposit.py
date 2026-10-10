"""«Новый депозит» карточкой-чеком: слева панель с воркером, справа сумма и строки.
От 1000 $ карточка золотая («КРУПНЫЙ ДЕПОЗИТ»).

Фоны и координаты рисует cards/render-deposit-bg.js (шаблон cards/deposit-card.html).
"""
import io
import json
from datetime import datetime
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .render import ASSETS, clean

BIG_DEPOSIT = 1000
DIR = ASSETS / "deposit"
THEMES = {
    "emerald": {"accent": (79, 220, 159), "hi": (233, 255, 245), "mid": (166, 245, 207), "glow": (60, 220, 150)},
    "gold": {"accent": (227, 194, 122), "hi": (255, 246, 220), "mid": (243, 220, 164), "glow": (230, 190, 100)},
}
TEXT = (234, 255, 245)
MUTED = (134, 169, 154)
DARK = (4, 23, 15)
# Inter: ascender 0.96875 em, line box of "normal" height 1.2109 em
ASC, LINE = 0.96875, 1.2109375


@lru_cache(maxsize=None)
def _layout():
    return json.loads((DIR / "layout.json").read_text("utf-8"))


@lru_cache(maxsize=None)
def _bg(theme):
    return Image.open(DIR / f"{theme}.jpg").convert("RGB")


@lru_cache(maxsize=64)
def _font(name, size):
    return ImageFont.truetype(str(ASSETS / "fonts" / f"Inter-{name}.otf"), max(int(size), 8))


def _width(text, font, spacing=0.0):
    return sum(font.getlength(c) + spacing for c in text) - (spacing if text else 0)


def _draw(draw, x, base, text, font, fill, spacing=0.0):
    """Текст по базовой линии, с межбуквенным интервалом; возвращает x после текста."""
    for c in text:
        draw.text((x, base), c, font=font, fill=fill, anchor="ls")
        x += font.getlength(c) + spacing
    return x - spacing


def _money(value):
    value = round(float(value), 2)
    s = f"{value:,.2f}".replace(",", " ")
    return s[:-3] if s.endswith(".00") else s


def _fit(text, name, size, spacing_em, max_w):
    while size > 10 and _width(text, _font(name, size), spacing_em * size) > max_w:
        size -= 1
    return _font(name, size), size


def _amount(img, lay, theme, amount, k):
    """$647 крупно: вертикальный градиент и свечение, как в шаблоне."""
    box = lay["amount"]
    text = _money(amount)
    size = 150
    while size > 40:
        big, small = _font("ExtraBold", size * k), _font("ExtraBold", size * 76 / 150 * k)
        w = _width("$", small) + 6 * k + _width(text, big, -4 * k * size / 150)
        if w <= lay["amount_max_w"] * k:
            break
        size -= 2
    x0, top = box["x"] * k, box["y"] * k
    base = top + (150 - size) * k / 2 + (size * (1 - LINE) / 2 + size * ASC) * k
    mask = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(mask)
    x = _draw(d, x0, base - 52 * size / 150 * k, "$", small, 255)
    _draw(d, x + 6 * k, base, text, big, 255, -4 * k * size / 150)

    c = THEMES[theme]
    glow = mask.filter(ImageFilter.GaussianBlur(12 * k)).point(lambda v: int(v * 0.45))
    img.paste(Image.new("RGB", img.size, c["glow"]), (0, 0), glow)

    h = int(box["h"] * k)
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        a, b, u = (c["hi"], c["mid"], t / 0.5) if t < 0.5 else (c["mid"], c["accent"], (t - 0.5) / 0.5)
        grad.putpixel((0, y), tuple(round(p + (q - p) * u) for p, q in zip(a, b)))
    fill = Image.new("RGB", img.size, c["hi"])
    fill.paste(grad.resize((img.size[0], h)), (0, int(top)))
    img.paste(fill, (0, 0), mask)


def new_deposit_card(worker, amount, number=None, method=None, payout=None, share=None,
                     day_total=None, when=None) -> bytes:
    """Картинка «Новый депозит». Все поля, кроме воркера и суммы, необязательные (иначе «—»)."""
    lay = _layout()
    k = lay["scale"]
    theme = "gold" if float(amount) >= BIG_DEPOSIT else "emerald"
    accent = THEMES[theme]["accent"]
    img = _bg(theme).copy()
    d = ImageDraw.Draw(img)

    # воркер на панели
    w = lay["worker"]
    name = clean(worker) or "—"
    font, size = _fit(name, "ExtraBold", 64 * k, -1 / 64, w["w"] * k)
    base = w["y"] * k + (64 * k - size) / 2 + size * (1 - LINE) / 2 + size * ASC
    _draw(d, w["x"] * k, base, name, font, DARK, -size / 64)

    # время
    t = lay["when"]
    when = when or datetime.now().strftime("%H:%M")
    f = _font("SemiBold", 20 * k)
    _draw(d, t["right"] * k - _width(when, f, k), t["y"] * k + 20 * k * ASC, when, f, MUTED, k)

    _amount(img, lay, theme, amount, k)

    # строки справа: номер, метод, выплата, итог дня
    rows = lay["rows"]
    bold, semi = _font("Bold", 24 * k), _font("SemiBold", 24 * k)
    max_w = (rows[0]["right"] - 1000) * k

    def right(row, parts):
        total = sum(_width(s, fnt) for s, fnt, _ in parts)
        x = row["right"] * k - total
        for s, fnt, color in parts:
            x = _draw(d, x, row["y"] * k + 24 * k * ASC, s, fnt, color)

    def value(text):
        text = clean(text) if text not in (None, "") else ""
        text = text or "—"
        while len(text) > 1 and _width(text, bold) > max_w:
            text = text[:-2] + "…"
        return [(text, bold, TEXT)]

    right(rows[0], value(f"#{number}" if number not in (None, "") else "—"))
    right(rows[1], value(method))
    if payout is None:
        right(rows[2], value(None))
    else:
        parts = [(f"${_money(payout)}", bold, TEXT)]
        if share not in (None, ""):
            parts += [(" ", bold, TEXT), (f"{_money(share)}%", semi, accent)]
        right(rows[2], parts)
    right(rows[3], value(None if day_total is None else f"${_money(day_total)}"))

    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return buf.getvalue()
