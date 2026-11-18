#!/usr/bin/env python3
"""November 18, 2026 -- The Day in Review.

Renders a one-page newspaper front page summing up the world news of
Wednesday, November 18, 2026, and writes it to /output/entry.png.

Pure Python standard library: no network, no third-party packages.
Text is drawn with a hand-built 5x7 bitmap font, rendered at 2x
supersampling and box-downsampled to 1024x1024 for smooth edges.
The PNG encoder is written by hand (zlib + struct), so two runs of
this program produce byte-identical output.
"""

import os
import struct
import zlib

W = 1024
H = 1024
SS = 2  # supersampling factor

# ---------------------------------------------------------------- font --
# Each glyph is 7 rows of 5 bits, "1" = ink.  Uppercase only: the whole
# front page is set in capitals, like a poster.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
}

# -------------------------------------------------------------- canvas --
class Canvas:
    """An RGB canvas in 1024-space coordinates, drawn at 2x internally."""

    def __init__(self, w=W, h=H):
        self.w = w
        self.h = h
        self.buf = bytearray(w * SS * h * SS * 3)

    def _put(self, x, y, r, g, b):
        # x, y are supersampled pixel coordinates.
        if 0 <= x < self.w * SS and 0 <= y < self.h * SS:
            i = (y * self.w * SS + x) * 3
            self.buf[i] = r
            self.buf[i + 1] = g
            self.buf[i + 2] = b

    def rect(self, x, y, w, h, color):
        """Filled rectangle; x, y, w, h in 1024-space units."""
        r, g, b = color
        x0 = max(0, int(x * SS))
        y0 = max(0, int(y * SS))
        x1 = min(self.w * SS, int((x + w) * SS))
        y1 = min(self.h * SS, int((y + h) * SS))
        for yy in range(y0, y1):
            base = yy * self.w * SS * 3
            for xx in range(x0, x1):
                i = base + xx * 3
                self.buf[i] = r
                self.buf[i + 1] = g
                self.buf[i + 2] = b

    def disc(self, cx, cy, rad, color):
        """Filled circle; centre and radius in 1024-space units."""
        r, g, b = color
        x0 = max(0, int((cx - rad) * SS))
        x1 = min(self.w * SS, int((cx + rad) * SS) + 1)
        y0 = max(0, int((cy - rad) * SS))
        y1 = min(self.h * SS, int((cy + rad) * SS) + 1)
        rr = rad * SS
        ccx = cx * SS
        ccy = cy * SS
        for yy in range(y0, y1):
            dy = yy + 0.5 - ccy
            for xx in range(x0, x1):
                dx = xx + 0.5 - ccx
                if dx * dx + dy * dy <= rr * rr:
                    i = (yy * self.w * SS + xx) * 3
                    self.buf[i] = r
                    self.buf[i + 1] = g
                    self.buf[i + 2] = b

    def line(self, x0, y0, x1, y1, width, color):
        """Thick line, stamped as discs along its length."""
        import math

        dx = x1 - x0
        dy = y1 - y0
        length = math.hypot(dx, dy)
        steps = max(1, int(length * SS))
        for s in range(steps + 1):
            t = s / steps
            self.disc(x0 + dx * t, y0 + dy * t, width / 2.0, color)

    def polygon(self, points, color):
        """Filled polygon via a scanline fill; points in 1024-space."""
        r, g, b = color
        pts = [(px * SS, py * SS) for px, py in points]
        ys = [p[1] for p in pts]
        y0 = max(0, int(min(ys)))
        y1 = min(self.h * SS, int(max(ys)) + 1)
        n = len(pts)
        for yy in range(y0, y1):
            yc = yy + 0.5
            xs = []
            for i in range(n):
                x1, y1p = pts[i]
                x2, y2p = pts[(i + 1) % n]
                if (y1p <= yc < y2p) or (y2p <= yc < y1p):
                    if y2p != y1p:
                        xs.append(x1 + (yc - y1p) * (x2 - x1) / (y2p - y1p))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                xa = max(0, int(xs[k]))
                xb = min(self.w * SS, int(xs[k + 1]) + 1)
                for xx in range(xa, xb):
                    i = (yy * self.w * SS + xx) * 3
                    self.buf[i] = r
                    self.buf[i + 1] = g
                    self.buf[i + 2] = b

    def downsample(self):
        """Average each SSxSS block into one 1024x1024 RGB frame."""
        out = bytearray(self.w * self.h * 3)
        sw = self.w * SS
        for y in range(self.h):
            for x in range(self.w):
                sr = sg = sb = 0
                for dy in range(SS):
                    base = ((y * SS + dy) * sw + x * SS) * 3
                    for dx in range(SS):
                        i = base + dx * 3
                        sr += self.buf[i]
                        sg += self.buf[i + 1]
                        sb += self.buf[i + 2]
                o = (y * self.w + x) * 3
                n = SS * SS
                out[o] = sr // n
                out[o + 1] = sg // n
                out[o + 2] = sb // n
        return bytes(out)

FONT.update({
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "*": ("00000", "10101", "01110", "10101", "00000", "00000", "00000"),
    # Bullet / middle dot, used as a separator between footer items.
    "•": ("00000", "00000", "01100", "01100", "00000", "00000", "00000"),
})


def text_width(text, scale):
    """Width in 1024-space units of text drawn at the given scale."""
    if not text:
        return 0
    return len(text) * 6 * scale - scale


def draw_text(cv, x, y, text, scale, color):
    """Draw uppercase text; x, y is the top-left corner."""
    text = text.upper()
    for ci, ch in enumerate(text):
        glyph = FONT.get(ch)
        if glyph is None:
            continue
        gx = x + ci * 6 * scale
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "1":
                    cv.rect(gx + col * scale, y + row * scale,
                            scale, scale, color)


def draw_text_centered(cv, cx, y, text, scale, color):
    draw_text(cv, cx - text_width(text, scale) // 2, y, text, scale, color)


def wrap_text(text, scale, max_width):
    """Greedy word wrap; returns a list of lines fitting max_width."""
    max_chars = max(1, max_width // (6 * scale))
    lines = []
    for para in text.split("\n"):
        words = para.split()
        cur = ""
        for word in words:
            trial = word if not cur else cur + " " + word
            if len(trial) <= max_chars:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                # A single over-long word is hard-split.
                while len(word) > max_chars:
                    lines.append(word[:max_chars])
                    word = word[max_chars:]
                cur = word
        if cur:
            lines.append(cur)
    return lines


def draw_block(cv, x, y, text, scale, max_width, color, leading=None):
    """Draw a wrapped paragraph; returns the y just below the block."""
    if leading is None:
        leading = 7 * scale + 4
    for line in wrap_text(text, scale, max_width):
        draw_text(cv, x, y, line, scale, color)
        y += leading
    return y

# --------------------------------------------------------------- png ---
def _chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return out


def encode_png(rgb, w, h):
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)  # filter: none
        raw += rgb[y * stride:(y + 1) * stride]
    idat = zlib.compress(bytes(raw), 9)
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", idat) + _chunk(b"IEND", b""))


# ------------------------------------------------------------ palette ---
PAPER = (246, 241, 229)
INK = (26, 26, 26)
MUTED = (96, 94, 86)
NAVY = (19, 42, 68)
NAVY_DARK = (12, 28, 48)
GOLD = (232, 184, 75)
GOLD_DARK = (176, 132, 38)
RED = (179, 38, 30)
WHITE = (255, 255, 255)
CARD = (255, 253, 247)
BORDER = (214, 208, 192)
BLUE = (29, 78, 216)
ORANGE = (180, 83, 9)
SLATE = (51, 65, 85)
PURPLE = (109, 40, 217)
SEA = (46, 111, 152)
SAND = (214, 186, 138)
BURST = (240, 128, 32)


def starburst(cv, cx, cy, r_out, r_in, spikes, color):
    """A jagged explosion star centred at (cx, cy)."""
    import math

    pts = []
    for i in range(spikes * 2):
        ang = math.pi * i / spikes - math.pi / 2
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    cv.polygon(pts, color)


def draw_card(cv, x, y, w, h, accent):
    cv.rect(x, y, w, h, CARD)
    cv.rect(x, y, w, 6, accent)
    cv.rect(x, y, w, 1, BORDER)
    cv.rect(x, y + h - 1, w, 1, BORDER)
    cv.rect(x, y, 1, h, BORDER)
    cv.rect(x + w - 1, y, 1, h, BORDER)


def draw_story(cv, x, y, w, h, accent, kicker, headline_lines, deck):
    draw_card(cv, x, y, w, h, accent)
    px = x + 20
    inner = w - 40
    draw_text(cv, px, y + 16, kicker, 2, accent)
    hy = y + 38
    for line in headline_lines:
        draw_text(cv, px, hy, line, 4, INK)
        hy += 32
    draw_block(cv, px, hy + 6, deck, 2, inner, MUTED)


def draw_lead_art(cv, x, y, w, h):
    """Stylised Gulf scene: dark sea, a sand island, a strike burst."""
    cv.rect(x, y, w, h, NAVY_DARK)
    cv.rect(x, y + int(h * 0.55), w, h - int(h * 0.55), SEA)
    cv.disc(x + 48, y + 40, 26, GOLD)
    # Qeshm island, low in the sea.
    cv.polygon([
        (x + 30, y + h - 34), (x + 120, y + h - 78),
        (x + 210, y + h - 66), (x + 268, y + h - 30),
        (x + 200, y + h - 12), (x + 90, y + h - 10),
    ], SAND)
    # Strike burst above the island.
    starburst(cv, x + 150, y + 108, 62, 26, 9, BURST)
    starburst(cv, x + 150, y + 108, 34, 14, 9, RED)
    cv.disc(x + 150, y + 108, 10, WHITE)
    # A jet diving away, with a trail.
    cv.line(x + 216, y + 52, x + 268, y + 30, 3, WHITE)
    cv.polygon([
        (x + 268, y + 22), (x + 296, y + 34), (x + 268, y + 42),
    ], WHITE)
    cv.rect(x, y + h - 28, w, 28, NAVY_DARK)
    draw_text(cv, x + 18, y + h - 22, "QESHM ISLAND", 2, WHITE)


def render():
    cv = Canvas()
    cv.rect(0, 0, W, H, PAPER)

    # Masthead.
    cv.rect(0, 0, W, 148, NAVY)
    draw_text_centered(cv, W // 2, 16, "THE WORLD TODAY", 7, WHITE)
    draw_text_centered(cv, W // 2, 80, "WEDNESDAY, NOVEMBER 18, 2026", 4, GOLD)
    draw_text_centered(cv, W // 2, 120,
                       "THE DAY IN REVIEW - SIX STORIES FROM AROUND THE WORLD",
                       2, (198, 204, 214))
    cv.rect(0, 148, W, 4, GOLD)

    # Lead story: Gulf escalation.
    lx, ly, lw, lh = 24, 164, 976, 288
    draw_card(cv, lx, ly, lw, lh, RED)
    draw_text(cv, lx + 24, ly + 16, "GULF - CONFLICT", 2, RED)
    hy = ly + 40
    for line in ("U.S. STRIKES IRAN", "MISSILE SITE ON", "QESHM ISLAND"):
        draw_text(cv, lx + 24, hy, line, 5, INK)
        hy += 40
    draw_block(cv, lx + 24, hy + 10,
               "JETS HIT A REVOLUTIONARY GUARD MISSILE SITE. IRAN THEN "
               "FIRED DRONES AT U.S. BASES IN BAHRAIN AND KUWAIT.",
               3, 580, INK)
    draw_lead_art(cv, lx + 648, ly + 16, 304, 256)

    # Four mid stories, 2 x 2.
    gy = 468
    gh = 164
    gw = 476
    draw_story(cv, 24, gy, gw, gh, BLUE, "UKRAINE - WAR",
               ("KERCH BRIDGE", "PARTLY FALLS"),
               "UKRAINIAN DRONES AND MISSILES HIT THE CRIMEA BRIDGE FOR A "
               "SECOND DAY. ONE ARCH FALLS INTO THE STRAIT.")
    draw_story(cv, 524, gy, gw, gh, ORANGE, "CHINA - APEC SUMMIT",
               ("XI AND PUTIN OPEN", "APEC IN SHENZHEN"),
               "THEY DENOUNCE SANCTIONS AND PROTECTIONISM. TRUMP JOINS "
               "THREE-WAY TALKS ON THURSDAY.")
    gy = 648
    draw_story(cv, 24, gy, gw, gh, SLATE, "UNITED STATES - POLITICS",
               ("PELTOLA WINS ALASKA", "SENATE SEAT"),
               "DEMOCRATS TAKE A 56-44 SENATE MAJORITY, THEIR LARGEST "
               "SINCE 2009.")
    draw_story(cv, 524, gy, gw, gh, RED, "UNITED STATES - HEALTH",
               ("MEASLES-FREE", "STATUS LOST"),
               "AFTER 26 YEARS, THE U.S. LOSES ITS MEASLES-FREE STATUS. "
               "5,412 CASES IN 2026, TEN DEATHS.")

    # Bottom row: Ebola and Voyager 1.
    by = 828
    bh = 124
    draw_card(cv, 24, by, gw, bh, PURPLE)
    draw_text(cv, 44, by + 12, "CONGO - HEALTH", 2, PURPLE)
    draw_text(cv, 44, by + 32, "EBOLA IN CONGO", 3, INK)
    draw_text(cv, 44, by + 57, "PASSES 11,000 CASES", 3, INK)
    draw_block(cv, 44, by + 86,
               "OUTBREAK MORE THAN DOUBLES IN THREE MONTHS. CHILDREN "
               "HARDEST HIT.", 2, gw - 40, MUTED)
    draw_card(cv, 524, by, gw, bh, NAVY)
    draw_text(cv, 544, by + 12, "SPACE - NASA", 2, NAVY)
    draw_text(cv, 544, by + 32, "VOYAGER 1 REACHES", 3, INK)
    draw_text(cv, 544, by + 57, "ONE LIGHT-DAY OUT", 3, INK)
    draw_block(cv, 544, by + 86,
               "FIRST HUMAN-MADE OBJECT 16 BILLION MILES FROM EARTH.",
               2, gw - 40, MUTED)

    # Footer strip: the rest of the day.
    cv.rect(0, 960, W, 64, NAVY)
    draw_block(cv, 24, 966,
               "ALSO TODAY: RUSSIAN MILITARY PLANE CRASHES IN SIBERIA, 19 "
               "DEAD \u2022 6.0 QUAKE HITS PAPUA NEW GUINEA \u2022 146,000 "
               "PROTEST IN FRANCE \u2022 CYCLONE XAVIER HITS COOK ISLANDS",
               2, 976, GOLD)
    return encode_png(cv.downsample(), W, H)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = render()
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes)" % (path, len(data)))


if __name__ == "__main__":
    main()
