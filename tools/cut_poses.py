"""Cut the challenge / attack / defeat poses out of each character sheet.

The sheets have a flat navy background. For each pose rectangle, background-coloured
pixels connected to the rectangle's edge become transparent (enclosed dark details stay),
title/label text is blanked, and the result is trimmed and saved as WebP with alpha in
assets/art/<name>_<pose>.webp.

    python tools/cut_poses.py            (writes all poses + assets/art/_check.png for review)
"""
from pathlib import Path
import numpy as np, cv2
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "assets" / "src" / "art", ROOT / "assets" / "art"
MAX_H = 420

# name: (poses {pose: (x0, y0, x1, y1)}, blank rects (titles, labels))
SHEETS = {
    "myvi": ({"challenge": (0, 0, 880, 952), "attack": (830, 0, 1536, 505), "defeat": (870, 540, 1536, 952)},
             [(0, 0, 395, 172)]),
    "hannah": ({"challenge": (150, 0, 720, 935), "attack": (760, 0, 1536, 540), "defeat": (860, 520, 1536, 955)},
               [(0, 0, 420, 200), (1215, 478, 1530, 522), (860, 520, 1080, 552)]),
    "matilda": ({"challenge": (40, 0, 660, 1062), "attack": (790, 20, 1374, 562), "defeat": (830, 620, 1374, 1058)},
                [(525, 25, 885, 200), (1010, 558, 1210, 598)]),
    "dominic": ({"challenge": (20, 30, 1010, 935), "attack": (1030, 80, 1522, 470), "defeat": (990, 500, 1536, 935)},
                [(545, 15, 1025, 192), (1340, 380, 1500, 425)]),
    # the player's graduate, back view, one panel per look (order matches LOOKS in game.html)
    "grad": ({"0": (36, 98, 604, 622), "1": (650, 98, 1218, 622), "2": (36, 662, 604, 1206), "3": (650, 662, 1218, 1206)},
             [(40, 105, 140, 182), (655, 105, 755, 182), (40, 668, 140, 748), (655, 668, 755, 748)]),
}


def cut(arr, rect, blanks, bg, tol=16):
    x0, y0, x1, y1 = rect
    a = arr[y0:y1, x0:x1].copy()
    for bx0, by0, bx1, by1 in blanks:                       # paint text areas with the background colour
        ix0, iy0, ix1, iy1 = max(bx0, x0) - x0, max(by0, y0) - y0, min(bx1, x1) - x0, min(by1, y1) - y0
        if ix1 > ix0 and iy1 > iy0: a[iy0:iy1, ix0:ix1] = bg
    near = (np.abs(a.astype(int) - bg).max(2) <= tol).astype(np.uint8)
    # background = near-bg pixels connected to the border
    n, lab = cv2.connectedComponents(near, connectivity=4)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bgmask = np.isin(lab, list(edge)) & (near > 0)
    alpha = np.where(bgmask, 0, 255).astype(np.uint8)
    # soften the cut edge by one pixel
    alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
    # drop tiny isolated specks (stray noise), keep sparkles of a few pixels
    n2, lab2, stats, _ = cv2.connectedComponentsWithStats((alpha > 128).astype(np.uint8), connectivity=8)
    for i in range(1, n2):
        if stats[i, cv2.CC_STAT_AREA] < 6: alpha[lab2 == i] = 0
    ys, xs = np.nonzero(alpha > 20)
    rgba = np.dstack([a, alpha])[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return Image.fromarray(rgba, "RGBA")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    checks = []
    for name, (poses, blanks) in SHEETS.items():
        arr = np.array(Image.open(next(SRC.glob(f"{name}_sheet.*"))).convert("RGB"))
        c = np.concatenate([arr[:8, :8].reshape(-1, 3), arr[-8:, -8:].reshape(-1, 3), arr[:8, -8:].reshape(-1, 3), arr[-8:, :8].reshape(-1, 3)])
        bg = np.median(c, 0).astype(np.uint8)
        for pose, rect in poses.items():
            im = cut(arr, rect, blanks, bg)
            if im.height > MAX_H: im = im.resize((round(im.width * MAX_H / im.height), MAX_H), Image.LANCZOS)
            p = OUT / f"{name}_{pose}.webp"
            im.save(p, "WEBP", quality=90, method=6)
            print(f"{p.name}: {im.size}, {p.stat().st_size // 1024} KB")
            checks.append(im)
    # review sheet on a bright checker so leftover background shows up
    W = sum(min(i.width, 300) for i in checks[:6]); rows = [checks[:6], checks[6:]]
    sheet = Image.new("RGB", (max(sum(int(i.width * 300 / i.height) for i in r) for r in rows), 600), (255, 0, 255))
    for ri, r in enumerate(rows):
        x = 0
        for i in r:
            t = i.resize((int(i.width * 300 / i.height), 300)); sheet.paste(t, (x, ri * 300), t); x += t.width
    sheet.save(OUT / "_check.png")


if __name__ == "__main__":
    main()
