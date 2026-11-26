#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Compose the SparkLing cards from the SparkQwen frame.

    make_cards.py BASE_DIR FONT.ttf OUT_DIR

BASE_DIR holds SparkQwen's `banner.png` and `social-preview.png`
(Enntity/sparkqwen docs/assets at commit bd26c6d). The frame, starfield,
logo, icons and tunnel are kept as they are; the title, version, subtitle,
lanes, supporting lines and URL are painted out and the new text (a
high-score table where the lanes were) is set in
Press Start 2P (SIL OFL 1.1, not shipped here). Adapted from SparkInkling's
make_cards.py. Needs Pillow. The JPEG is a format export of the social card.
"""
import json
import random
import re
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

WHITE, YELLOW, ORANGE = (255, 255, 255), (255, 232, 26), (255, 150, 40)
PURPLE, VIOLET, DIM = (190, 120, 255), (150, 90, 235), (170, 170, 190)
LINK = (160, 120, 255)
STAR_COLORS = [WHITE] * 5 + [YELLOW] * 3 + [(170, 100, 255), (90, 220, 255)]
# The title's two words: top and bottom of the fill gradient, then the shadow.
SPARK = ((255, 236, 60), (255, 120, 20), (190, 60, 0))
LING = ((210, 255, 247), (58, 216, 217), (13, 107, 139))


class Card:
    def __init__(self, base, font_path):
        self.im = Image.open(base).convert("RGB")
        self.font_path = font_path
        self.draw = ImageDraw.Draw(self.im)
        self.cleared, self.inked = [], []

    def font(self, size):
        return ImageFont.truetype(self.font_path, size)

    def clear(self, box, stars=True):
        """Paint a region black; `stars` refills it once the text is set."""
        self.draw.rectangle(box, fill=(0, 0, 0))
        if stars:
            self.cleared.append(box)

    def clear_warm(self, box, stars=None):
        """Paint out only a region's warm pixels (the old version and its
        orange glow), so the tunnel's dim blue haze beside it keeps no edge.
        `stars` is the part that gets new stars."""
        region = self.im.crop(box)
        r, _, b = region.split()
        ink = ImageChops.subtract(r, b).point(lambda v: 255 if v > 2 else 0)
        region.paste((0, 0, 0), mask=ink.filter(ImageFilter.MaxFilter(9)))
        self.im.paste(region, box[:2])
        self.draw = ImageDraw.Draw(self.im)
        if stars:
            self.cleared.append(stars)

    def stars(self, seed, pad=14):
        """Scatter stars over the cleared regions at the base card's density, clear of the text."""
        rng = random.Random(seed)
        for x0, y0, x1, y1 in self.cleared:
            if x1 - x0 < 40 or y1 - y0 < 40:
                continue
            for _ in range(max(1, (x1 - x0) * (y1 - y0) // 24000)):
                s = rng.choice([3, 3, 4, 5])
                x, y = rng.randrange(x0 + 6, x1 - s - 6), rng.randrange(y0 + 6, y1 - s - 6)
                if not any(a - pad < x < c + pad and b - pad < y < d + pad for a, b, c, d in self.inked):
                    self.draw.rectangle((x, y, x + s, y + s), fill=rng.choice(STAR_COLORS))

    def text(self, xy, parts, size, color, glow=None, gap=None):
        """Draw `parts` left to right from `xy`, a square dot between them."""
        font = self.font(size)
        gap = size if gap is None else gap
        width = sum(int(font.getlength(p)) for p in parts) + 2 * gap * (len(parts) - 1)
        self.draw.rectangle((xy[0] - 8, xy[1] - 8, xy[0] + width + 8, xy[1] + size + 8), fill=(0, 0, 0))
        layer = Image.new("RGB", self.im.size, (0, 0, 0))
        d = ImageDraw.Draw(layer)
        x, y = xy
        for i, part in enumerate(parts):
            if i:
                dot = max(3, size // 5)
                cy = y + size // 2
                d.rectangle((x + gap - dot // 2, cy - dot // 2, x + gap + dot - dot // 2, cy + dot - dot // 2), fill=color)
                x += 2 * gap
            d.text((x, y), part, font=font, fill=color)
            x += int(font.getlength(part))
        if glow:
            tint = Image.new("RGB", self.im.size, glow)
            mask = layer.convert("L").point(lambda v: 255 if v else 0)
            halo = Image.composite(tint, Image.new("RGB", self.im.size, (0, 0, 0)), mask)
            halo = halo.filter(ImageFilter.GaussianBlur(max(2, size // 5)))
            self.im = ImageChops.screen(self.im, halo)
        self.im = ImageChops.lighter(self.im, layer) if not glow else Image.composite(
            layer, self.im, layer.convert("L").point(lambda v: 255 if v else 0))
        self.draw = ImageDraw.Draw(self.im)
        self.inked.append((xy[0], y, x, y + size))
        return x

    def title(self, xy, words, size):
        """The product name in blocky pixel letters: each word a vertical
        gradient over a stepped drop shadow, in the spirit of the base card's
        lettering."""
        font = self.font(size)
        x, y = xy
        depth = max(4, size // 14)
        for word, (top, bottom, shadow) in words:
            w = int(font.getlength(word))
            mask = Image.new("L", self.im.size, 0)
            ImageDraw.Draw(mask).text((x, y), word, font=font, fill=255)
            for step in range(depth, 0, -1):
                self.im.paste(shadow, mask=ImageChops.offset(mask, step, step))
            fill = Image.new("RGB", self.im.size)
            fd = ImageDraw.Draw(fill)
            for row in range(size + 1):
                t = row / size
                fd.line((x, y + row, x + w, y + row),
                        fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
            self.im.paste(fill, mask=mask)
            x += w
        self.draw = ImageDraw.Draw(self.im)
        self.inked.append((xy[0], y, x + depth, y + size + depth))
        return x

    def rule(self, x, y0, y1):
        self.draw.rectangle((x, y0, x + 2, y1), fill=(170, 60, 230))
        self.inked.append((x, y0, x + 2, y1))


PINK = (255, 70, 120)
def scores(card, x0, y, k, ky, data):
    """Show the 0.1.1 release's one-stream and eight-stream decode and its shared cache for both models."""
    head, small, label, num = int(21 * k), int(13 * k), int(23 * k), int(31 * k)
    cols = [("LING", "8 x 256K", x0 + int(800 * k)),
            ("LINGSANTE", "8 x 128K", x0 + int(1200 * k))]
    workloads = [("1 STREAM TOK/S", "one", "{:.1f}"), ("8 STREAMS TOK/S", "eight", "{:.1f}"),
                 ("CACHE TOKENS", "cache", "{:.2f}M")]

    def right(xr, yy, s, size, color, glow=None):
        card.text((xr - int(card.font(size).getlength(s)), yy), [s], size, color, glow=glow)

    card.text((x0, y), ["HIGH SCORES"], head, PINK, glow=(150, 20, 70))
    for name, cmd, xr in cols:
        right(xr, y, name, head, WHITE)
        right(xr, y + int(30 * ky), cmd, small, VIOLET)
    line = y + int(54 * ky)
    card.draw.rectangle((x0, line, cols[-1][2], line + 2), fill=(170, 60, 230))
    card.inked.append((x0, line, cols[-1][2], line + 2))
    for row, (name, key, form) in enumerate(workloads):
        yy = y + int(72 * ky) + row * int(42 * ky)
        card.text((x0, yy + (num - label) // 2), [name], label, WHITE)
        for rates, (_, _, xr) in zip(data, cols):
            right(xr, yy, form.format(rates[key]), num, YELLOW, glow=ORANGE)


LINES = (["Exact native MTP", "same text drafted or not"],
         ["Text", "images", "video", "tools"],
         ["./start.sh up", "lloom setup"])
SOURCE = ["0.1.1", "256 greedy tokens per stream", "25 NOV 2026"]
URL = "github.com/Enntity/SparkLing"


def banner(base, font, out, data):
    c = Card(base, font)
    c.clear_warm((1062, 60, 1540, 244), (1075, 70, 1480, 240))  # the old version
    c.clear((75, 92, 1062, 244), stars=False)  # the old title
    c.clear((75, 244, 1430, 520))         # subtitle and lanes
    c.clear((150, 521, 1200, 700))        # supporting lines (icons stay)
    c.clear((1550, 636, 2110, 688), stars=False)  # the URL (the GitHub mark stays)
    c.title((88, 112), [("Spark", SPARK), ("Ling", LING)], 112)
    c.text((88, 270), ["Ling + LingSante-VL on one DGX Spark", "Atlas"], 23, WHITE)
    scores(c, 100, 326, 1.0, 1.0, data)
    for y, parts in zip((537, 580, 624), LINES):
        c.text((172, y), parts, 20, WHITE)
    c.text((172, 668), SOURCE, 14, DIM, gap=10)
    c.text((1562, 648), [URL], 17, LINK)
    c.stars(1)
    c.im.save(out, optimize=True)


def social(base, font, out, data):
    c = Card(base, font)
    c.clear_warm((866, 130, 1215, 250), (880, 140, 1150, 285))  # the old version,
    c.clear_warm((866, 250, 1185, 268))                         # stepped along
    c.clear_warm((866, 268, 1160, 292))                         # the tunnel's edge
    c.clear_warm((1185, 250, 1202, 260))
    c.clear_warm((1160, 268, 1174, 280))
    c.clear((70, 150, 880, 292), stars=False)  # the old title
    c.clear((70, 292, 1136, 585))         # subtitle and lanes
    c.clear((150, 596, 1050, 815))        # supporting lines (icons stay)
    c.clear((1140, 784, 1690, 830), stars=False)  # the URL (the GitHub mark stays)
    c.title((80, 178), [("Spark", SPARK), ("Ling", LING)], 86)
    c.text((82, 312), ["Ling + LingSante-VL on one DGX Spark", "Atlas"], 19, WHITE)
    scores(c, 82, 380, 0.84, 1.08, data)
    for y, parts in zip((618, 668, 718), LINES):
        c.text((170, y), parts, 17, WHITE, gap=12)
    c.text((170, 770), SOURCE, 13, DIM, gap=9)
    c.text((1150, 797), [URL], 16, LINK)
    c.stars(2)
    c.im.save(out, optimize=True)
    c.im.save(Path(out).with_suffix(".jpg"), quality=90)


if __name__ == "__main__":
    base, font, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    results = Path(__file__).resolve().parents[2] / "results/2026-11-25-0.1.1/release"
    data = []
    for model in ("ling", "sante"):
        rows = lambda name: [json.loads(l) for l in (results / f"{model}-spark-{name}.jsonl").read_text().splitlines()]
        probes = rows("probe")
        kv = re.search(r"= (\d+) max KV tokens", (results / f"{model}-spark-server-kv.log").read_text())
        data.append({
            "one": sum(r["tok_s"] for r in probes) / len(probes),  # mean of the eight probe prompts
            "eight": next(r["aggregate_tok_s"] for r in rows("conc") if r["clients"] == 8),
            "cache": int(kv.group(1)) / 1e6,
        })
    banner(base / "banner.png", font, out / "banner.png", data)
    social(base / "social-preview.png", font, out / "social-preview.png", data)
