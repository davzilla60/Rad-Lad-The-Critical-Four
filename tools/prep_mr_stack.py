"""Turn a DICOM MR case (e.g. ISLES-2022) into slice images for the game's scrollable viewer.

The reference series (DWI here) defines the axial planes. Other series (FLAIR, often a
sagittal 3-D acquisition) are resampled onto those same planes using the DICOM geometry,
so every series scrolls in step and the lesion mask lines up with all of them.

    python tools/prep_mr_stack.py <case folder> <out folder> --ref DWI --series DWI FLAIR --mask Lesion_Mask

Writes <out>/<SERIES>/NNN.png (8-bit, windowed) and <out>/<SERIES>_mask/NNN.png (white-on-black,
same size as that series' slices). Slice 000 is the most inferior.
"""
import argparse, glob, os
import numpy as np, pydicom
from PIL import Image
from scipy.ndimage import map_coordinates


def load(folder):
    ds = [pydicom.dcmread(f) for f in glob.glob(os.path.join(folder, "*.dcm"))]
    iop = np.array(ds[0].ImageOrientationPatient, float)
    r, c = iop[:3], iop[3:]
    n = np.cross(r, c)
    ds.sort(key=lambda d: float(np.dot(np.array(d.ImagePositionPatient, float), n)))
    vol = np.stack([d.pixel_array.astype(np.float32) * float(d.get("RescaleSlope", 1)) + float(d.get("RescaleIntercept", 0)) for d in ds])
    ipp0 = np.array(ds[0].ImagePositionPatient, float)
    dr, dc = (float(v) for v in ds[0].PixelSpacing)          # row spacing, column spacing
    dz = float(np.dot(np.array(ds[1].ImagePositionPatient, float) - ipp0, n)) if len(ds) > 1 else 1.0
    # voxel (k, i, j) -> patient: ipp0 + j*dc*r + i*dr*c + k*dz*n
    return {"vol": vol, "ipp0": ipp0, "r": r, "c": c, "n": n, "dr": dr, "dc": dc, "dz": dz}


def patient_to_index(s, pts):
    d = pts - s["ipp0"]
    return np.stack([d @ s["n"] / s["dz"], d @ s["c"] / s["dr"], d @ s["r"] / s["dc"]])   # k, i, j


def window(vol, lo_pct=0.5, hi_pct=99.7):
    v = vol[vol > np.percentile(vol, 60)]          # ignore the background when picking the window
    lo, hi = np.percentile(v, lo_pct), np.percentile(v, hi_pct)
    return np.clip((vol - lo) / max(hi - lo, 1e-6) * 255, 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case"); ap.add_argument("out")
    ap.add_argument("--ref", default="DWI"); ap.add_argument("--series", nargs="+", default=["DWI", "FLAIR"])
    ap.add_argument("--mask", default="Lesion_Mask"); ap.add_argument("--step", type=int, default=1); ap.add_argument("--inplane", type=float, default=0.75)
    a = ap.parse_args()
    ref = load(os.path.join(a.case, a.ref))
    K, Hr, Wr = ref["vol"].shape
    # target grid: the reference planes, resampled in-plane to --inplane mm
    H, Wd = int(round(Hr * ref["dr"] / a.inplane)), int(round(Wr * ref["dc"] / a.inplane))
    ii, jj = np.meshgrid((np.arange(H) + .5) * a.inplane / ref["dr"] - .5, (np.arange(Wd) + .5) * a.inplane / ref["dc"] - .5, indexing="ij")
    msk = load(os.path.join(a.case, a.mask)) if a.mask else None
    crop = None   # square box around the head, taken from the reference series, shared by all series
    for name in [a.ref] + [n for n in a.series if n != a.ref]:
        src = ref if name == a.ref else load(os.path.join(a.case, name))
        os.makedirs(os.path.join(a.out, name), exist_ok=True)
        os.makedirs(os.path.join(a.out, name + "_mask"), exist_ok=True)
        slices, masks = [], []
        for k in range(0, K, a.step):
            pts = ref["ipp0"] + (k * ref["dz"]) * ref["n"] + (jj[..., None] * ref["dc"]) * ref["r"] + (ii[..., None] * ref["dr"]) * ref["c"]
            idx = patient_to_index(src, pts.reshape(-1, 3))
            slices.append(map_coordinates(src["vol"], idx, order=1, mode="constant", cval=0).reshape(H, Wd))
            if msk is not None:
                midx = patient_to_index(msk, pts.reshape(-1, 3))
                # any non-zero label counts (multi-label tumour masks: core, oedema, enhancing)
                masks.append(map_coordinates((msk["vol"] > 0).astype(np.float32), midx, order=1, mode="constant").reshape(H, Wd) > .5)
        img = window(np.stack(slices))
        if crop is None:
            ys, xs = np.nonzero(img.max(0) > 12)
            cy, cx = (ys.min() + ys.max()) / 2, (xs.min() + xs.max()) / 2
            half = int(max(ys.max() - ys.min(), xs.max() - xs.min()) / 2 + 8)
            y0, x0 = max(0, int(cy) - half), max(0, int(cx) - half)
            crop = (y0, min(H, y0 + 2 * half), x0, min(Wd, x0 + 2 * half))
        y0, y1, x0, x1 = crop
        for k in range(len(img)):
            Image.fromarray(img[k, y0:y1, x0:x1]).save(os.path.join(a.out, name, f"{k:03d}.png"))
            if msk is not None: Image.fromarray((masks[k][y0:y1, x0:x1] * 255).astype(np.uint8)).save(os.path.join(a.out, name + "_mask", f"{k:03d}.png"))
        hit = [k for k in range(len(masks)) if masks[k].any()]
        print(name, img.shape, "lesion slices:", (hit[0], hit[-1]) if hit else None, "count", len(hit))


if __name__ == "__main__":
    main()
