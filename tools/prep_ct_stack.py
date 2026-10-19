"""Turn a thin-slice DICOM CT (plus an optional label series on the same grid) into a
scrollable stack for the game: averaged slabs, windowed to 8-bit, cropped to the body.

    python tools/prep_ct_stack.py <CT folder> <out folder> --seg <SEG folder> --slab 3 --window 600 150 --label "CTA"

Writes <out>/<label>/NNN.png and <out>/<label>_mask/NNN.png. Slice 000 is the most superior
(the usual PACS order for axial CT). With --seg, the stack is limited to the labelled
structure plus --margin mm above and below.
"""
import argparse, glob, os
import numpy as np, pydicom
from PIL import Image


def load(folder):
    ds = [pydicom.dcmread(f) for f in glob.glob(os.path.join(folder, "**", "*.dcm"), recursive=True)]
    ds.sort(key=lambda d: -float(d.ImagePositionPatient[2]))           # superior first
    z = np.array([float(d.ImagePositionPatient[2]) for d in ds])
    vol = np.stack([d.pixel_array.astype(np.float32) * float(d.get("RescaleSlope", 1) or 1) + float(d.get("RescaleIntercept", 0) or 0) for d in ds])
    return vol, z, [float(v) for v in ds[0].PixelSpacing]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ct"); ap.add_argument("out")
    ap.add_argument("--seg"); ap.add_argument("--slab", type=float, default=3.0)
    ap.add_argument("--window", type=float, nargs=2, default=[600, 150], metavar=("WIDTH", "LEVEL"))
    ap.add_argument("--margin", type=float, default=20.0); ap.add_argument("--size", type=int, default=384)
    ap.add_argument("--label", default="CTA")
    ap.add_argument("--mat", help="label volume in a MATLAB .mat file instead of --seg (e.g. FUMPE ground truth): "
                                  "array (rows, cols, slices) with slices in the CT folder's filename order")
    ap.add_argument("--mat-key", default="Mask")
    a = ap.parse_args()
    vol, z, sp = load(a.ct)
    vol[vol < -1024] = -1024                                             # outside the scan field of view
    seg = None
    if a.mat:
        import scipy.io as sio
        m = sio.loadmat(a.mat)[a.mat_key].transpose(2, 0, 1).astype(np.float32)        # (slice, row, col), filename order
        files = sorted(glob.glob(os.path.join(a.ct, "**", "*.dcm"), recursive=True))
        zf = np.array([float(pydicom.dcmread(f, stop_before_pixels=True).ImagePositionPatient[2]) for f in files])
        assert len(zf) == len(m), f"{len(m)} mask slices for {len(zf)} CT slices"
        seg = m[np.argsort(-zf)]                                                    # same superior-first order as load()
        hit = np.where(seg.reshape(len(seg), -1).max(1) > 0)[0]
        lo, hi = z.max(), z.min()
    elif a.seg:
        seg, zs, _ = load(a.seg)
        assert np.allclose(z, zs, atol=.01), "SEG and CT slices do not line up"
        hit = np.where(seg.reshape(len(seg), -1).max(1) > 0)[0]
        lo, hi = z[hit].max() + a.margin, z[hit].min() - a.margin      # superior, inferior limits (mm)
    else:
        lo, hi = z.max(), z.min()
    edges = np.arange(lo, hi - a.slab, -a.slab)
    W, L = a.window
    slabs, masks = [], []
    for top in edges:
        sel = (z <= top) & (z > top - a.slab)
        if not sel.any(): continue
        slabs.append(vol[sel].mean(0))
        if seg is not None: masks.append((seg[sel] > 0).mean(0) >= .5)
    img = np.clip((np.stack(slabs) - (L - W / 2)) / W * 255, 0, 255).astype(np.uint8)
    body = np.stack(slabs).max(0) > -400
    ys, xs = np.nonzero(body)
    cy, cx = (ys.min() + ys.max()) // 2, (xs.min() + xs.max()) // 2
    half = max(ys.max() - ys.min(), xs.max() - xs.min()) // 2 + 6
    y0, x0 = max(0, cy - half), max(0, cx - half)
    y1, x1 = min(img.shape[1], y0 + 2 * half), min(img.shape[2], x0 + 2 * half)
    os.makedirs(os.path.join(a.out, a.label), exist_ok=True)
    if seg is not None: os.makedirs(os.path.join(a.out, a.label + "_mask"), exist_ok=True)
    for k in range(len(img)):
        im = Image.fromarray(img[k, y0:y1, x0:x1])
        if max(im.size) > a.size:                                        # keep the aspect ratio
            f = a.size / max(im.size); im = im.resize((round(im.width * f), round(im.height * f)), Image.LANCZOS)
        im.save(os.path.join(a.out, a.label, f"{k:03d}.png"))
        if seg is not None:
            m = Image.fromarray((masks[k][y0:y1, x0:x1] * 255).astype(np.uint8)).resize(im.size, Image.NEAREST)
            m.save(os.path.join(a.out, a.label + "_mask", f"{k:03d}.png"))
    print(f"{len(img)} slabs of {a.slab} mm, crop {x1 - x0}x{y1 - y0} px -> {im.size}, z {lo:.0f} to {hi:.0f} mm")


if __name__ == "__main__":
    main()
