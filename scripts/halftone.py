"""
Halftone portrait generator for your GitHub profile README.

- Downloads the avatar of the GitHub user (generic: reads username from env)
- Converts it to a halftone dot portrait (rotated 45° dot grid)
- Saves to assets/portrait.png

Env vars (all optional):
  GH_USER   GitHub username (default: GITHUB_REPOSITORY_OWNER)
  THEME     "light" -> black dots on white (default) | "dark" -> green dots on dark
  CELL      dot grid spacing in px (default 7)
  SIZE      output size in px (default 900)
  SRC       local image path (skip download; useful for testing)
"""
import io
import math
import os
import sys
import urllib.request

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

USER = os.getenv("GH_USER") or os.getenv("GITHUB_REPOSITORY_OWNER") or "Jatin-Purbia"
THEME = os.getenv("THEME", "light").lower()
CELL = float(os.getenv("CELL", "7"))
SIZE = int(os.getenv("SIZE", "900"))
SRC = os.getenv("SRC")
OUT = os.getenv("OUT", "assets/portrait.png")
SS = 2  # supersampling for smooth dots

PALETTE = {
    "light": {"bg": (255, 255, 255), "dot": (13, 17, 23)},
    "dark": {"bg": (13, 17, 23), "dot": (57, 211, 83)},
}[THEME if THEME in ("light", "dark") else "light"]


def load_avatar() -> Image.Image:
    if SRC:
        return Image.open(SRC).convert("RGB")
    url = f"https://github.com/{USER}.png?size=800"
    req = urllib.request.Request(url, headers={"User-Agent": "halftone-profile"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return Image.open(io.BytesIO(r.read())).convert("RGB")


def prepare(img: Image.Image) -> Image.Image:
    img = ImageOps.fit(img, (SIZE * SS, SIZE * SS), Image.LANCZOS, centering=(0.5, 0.4))
    g = ImageOps.grayscale(img)
    g = ImageOps.autocontrast(g, cutoff=2)
    g = ImageEnhance.Contrast(g).enhance(1.25)
    g = g.filter(ImageFilter.GaussianBlur(radius=SS))  # average tone per dot
    return g


def halftone(gray: Image.Image) -> Image.Image:
    w, h = gray.size
    px = gray.load()
    out = Image.new("RGB", (w, h), PALETTE["bg"])
    d = ImageDraw.Draw(out)

    step = CELL * SS
    max_r = step * 0.72
    ang = math.radians(45)
    ca, sa = math.cos(ang), math.sin(ang)
    cx, cy = w / 2, h / 2
    n = int(math.hypot(w, h) / step) + 2

    for i in range(-n, n):
        for j in range(-n, n):
            u, v = i * step, j * step
            x = cx + u * ca - v * sa
            y = cy + u * sa + v * ca
            if not (0 <= x < w and 0 <= y < h):
                continue
            tone = px[int(x), int(y)] / 255.0
            # light theme: dark areas -> big dots; dark theme: bright areas -> big dots
            amount = (1 - tone) if THEME != "dark" else tone
            r = max_r * math.sqrt(max(0.0, min(1.0, amount)))
            if r < 0.6 * SS:
                continue
            d.ellipse((x - r, y - r, x + r, y + r), fill=PALETTE["dot"])

    return out.resize((SIZE, SIZE), Image.LANCZOS)


def main():
    try:
        avatar = load_avatar()
    except Exception as e:
        print(f"Could not load avatar: {e}", file=sys.stderr)
        sys.exit(1)
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    halftone(prepare(avatar)).save(OUT, optimize=True)
    print(f"Saved {OUT} for {USER} ({THEME})")


if __name__ == "__main__":
    main()
