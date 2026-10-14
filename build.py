"""Build index.html / critical-four.embed.html from game.html + the case list below.

Every case belongs to one opponent (domonic, matilda, hannah, myvi, lightbox) and has
one or more image SERIES. A series is either a single image (an X-ray view) or a
folder of slices (a scrollable CT/MRI stack):

    {"label": "PA",          "file": "dom1/pa.png"}       one image
    {"label": "Axial brain", "dir":  "mat1/axial"}        every image in that folder,
                                                          in natural filename order
                                                          (slice_2 before slice_10)
    {"label": "Axial", "dir": "mat1/axial", "reverse": True}   flip the order if the
                                                          export runs feet-to-head

Paths are relative to assets/src/. The build converts everything to greyscale JPEG
in assets/cases/<id>/ and, for the full build, inlines it so the output is one
self-contained file.

A case with "placeholder": True needs no images: the game draws a labelled stand-in
film (or a fake scrollable stack for CT/MRI) so the whole flow can be played before
the real studies arrive.

Usage:  python build.py            -> index.html + critical-four.embed.html (self-contained)
        python build.py --preview  -> _preview.html (references assets/cases/ files; for local testing)
"""
import base64, json, re, sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).parent
A = ROOT / "assets"
XRAY_SIDE, STACK_SIDE = 1400, 768
OPPONENTS = ["domonic", "matilda", "hannah", "myvi", "lightbox"]


def ph(cid, opp, modality, label):
    """A placeholder case: same shape as a real one, so swapping in real content is a straight edit."""
    return {
        "id": cid, "opponent": opp, "modality": modality, "label": label, "placeholder": True,
        "history": "Clinical history to be added.",
        "question": "What is the urgent finding?",
        "options": ["Answer A (correct, placeholder)", "Answer B", "Answer C", "Answer D"],
        "answer": 0,
        "finding": "Finding to be added.",
        "clue": "Key imaging clue to be added.",
        "why": "Why it matters to be added.",
        "series": [], "source": None,
    }


# ---------------------------------------------------------------------------------
# THE 30 CASES. Each opponent has exactly six.
#   modality  "X-ray", "CT" or "MRI" (CT/MRI with a multi-slice series count as
#             scrollable, which matters for the "Scroll Model" marker)
#   label     shown above the study, e.g. "Chest X-ray, PA"
#   history   one-line clinical context shown with the question
#   options   exactly four; "answer" is the index of the correct one (0-3).
#             The game shuffles the order on screen.
#   finding / clue / why   the three-part explanation shown once the case is solved
#   series    list of series in viewing order (see top of file)
#   source    key into SOURCES for the image credit, or None
# ---------------------------------------------------------------------------------
CASES = [
    # Domonic: chest pathology and chest lines/tubes
    ph("dom1", "domonic", "X-ray", "Chest X-ray, PA"),
    ph("dom2", "domonic", "X-ray", "Chest X-ray, AP supine"),
    ph("dom3", "domonic", "X-ray", "Chest X-ray, AP (lines and tubes)"),
    ph("dom4", "domonic", "X-ray", "Chest X-ray, AP (lines and tubes)"),
    ph("dom5", "domonic", "X-ray", "Chest X-ray, PA"),
    ph("dom6", "domonic", "CT", "CT chest, axial"),
    # Matilda: neurological emergencies
    ph("mat1", "matilda", "CT", "CT head, non-contrast"),
    ph("mat2", "matilda", "CT", "CT head, non-contrast"),
    ph("mat3", "matilda", "CT", "CT angiogram, circle of Willis"),
    ph("mat4", "matilda", "MRI", "MRI brain, DWI"),
    ph("mat5", "matilda", "CT", "CT head, non-contrast"),
    ph("mat6", "matilda", "MRI", "MRI spine, sagittal T2"),
    # Hannah: abdominal and vascular emergencies
    ph("han1", "hannah", "X-ray", "Abdominal X-ray, supine"),
    ph("han2", "hannah", "X-ray", "Chest X-ray, erect"),
    ph("han3", "hannah", "CT", "CT abdomen and pelvis, portal venous"),
    ph("han4", "hannah", "CT", "CT aortogram"),
    ph("han5", "hannah", "CT", "CT abdomen and pelvis"),
    ph("han6", "hannah", "CT", "CT abdomen, arterial phase"),
    # My-Vi: musculoskeletal
    ph("myv1", "myvi", "X-ray", "Pelvis, AP"),
    ph("myv2", "myvi", "X-ray", "Elbow, lateral"),
    ph("myv3", "myvi", "X-ray", "Wrist, PA"),
    ph("myv4", "myvi", "X-ray", "Ankle, AP"),
    ph("myv5", "myvi", "CT", "CT cervical spine, sagittal"),
    ph("myv6", "myvi", "MRI", "MRI knee, sagittal PD"),
    # The Lightbox (champion): mixed
    ph("lbx1", "lightbox", "X-ray", "Chest X-ray, PA"),
    ph("lbx2", "lightbox", "CT", "CT head, non-contrast"),
    ph("lbx3", "lightbox", "CT", "CT abdomen and pelvis"),
    ph("lbx4", "lightbox", "X-ray", "Shoulder, AP"),
    ph("lbx5", "lightbox", "MRI", "MRI brain"),
    ph("lbx6", "lightbox", "X-ray", "Abdominal X-ray"),
]

# Image source attribution, keyed by each case's "source".
SOURCES = {
    # "example": {
    #     "citation": "Author (Year). Title. Publisher.",
    #     "url": "https://doi.org/...",
    #     "licence": "CC BY 4.0", "licence_url": "https://creativecommons.org/licenses/by/4.0/",
    #     "changes": "converted to greyscale JPEG",
    # },
}

IMG_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


def natural(p):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]


def series_files(s):
    if "file" in s:
        return [A / "src" / s["file"]]
    files = sorted((f for f in (A / "src" / s["dir"]).iterdir() if f.suffix.lower() in IMG_EXT), key=natural)
    return files[::-1] if s.get("reverse") else files


def data_uri(p):
    mime = "image/png" if p.suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def check(c):
    errs = []
    if c["opponent"] not in OPPONENTS: errs.append(f"unknown opponent {c['opponent']!r}")
    if len(c["options"]) != 4: errs.append(f"needs 4 options, has {len(c['options'])}")
    if not 0 <= c["answer"] < len(c["options"]): errs.append("answer index out of range")
    if len(set(c["options"])) != len(c["options"]): errs.append("duplicate options")
    if not c.get("placeholder") and not c["series"]: errs.append("no series (add images or mark it a placeholder)")
    return errs


def main():
    preview = "--preview" in sys.argv
    bad = False
    for c in CASES:
        for e in check(c):
            print(f"!! {c['id']}: {e}"); bad = True
    for o in OPPONENTS:
        n = sum(c["opponent"] == o for c in CASES)
        if n != 6: print(f"!! {o} has {n} case(s); the game expects 6"); bad = True
    if bad: sys.exit(1)

    out_cases = []
    for c in CASES:
        e = {k: v for k, v in c.items() if k != "series"}
        e["series"] = []
        for si, s in enumerate(c["series"]):
            files = series_files(s)
            if not files: sys.exit(f"!! {c['id']}: series {s['label']!r} has no images")
            side = XRAY_SIDE if len(files) == 1 else STACK_SIDE
            d = A / "cases" / c["id"]; d.mkdir(parents=True, exist_ok=True)
            imgs = []
            for k, f in enumerate(files):
                im = Image.open(f).convert("L")
                if max(im.size) > side: im.thumbnail((side, side), Image.LANCZOS)
                p = d / f"s{si}_{k:03d}.jpg"
                im.save(p, "JPEG", quality=84 if len(files) == 1 else 80, optimize=True)
                imgs.append(f"assets/cases/{c['id']}/{p.name}" if preview else data_uri(p))
            e["series"].append({"label": s["label"], "images": imgs})
        out_cases.append(e)

    used = {c["source"] for c in CASES if c.get("source")}
    sources = {k: v for k, v in SOURCES.items() if k in used}
    assets = {"logo_mark": data_uri(A / "logo_mark.png")}
    src = (ROOT / "game.html").read_text(encoding="utf-8")
    out = (src.replace("/*__CASES__*/[]", json.dumps(out_cases))
              .replace("/*__SOURCES__*/{}", json.dumps(sources))
              .replace("/*__ASSETS__*/{}", json.dumps(assets)))
    names = ["_preview.html"] if preview else ["index.html", "critical-four.embed.html"]
    for n in names:
        (ROOT / n).write_text(out, encoding="utf-8")
    for o in OPPONENTS:
        cs = [c for c in CASES if c["opponent"] == o]
        real = sum(not c.get("placeholder") for c in cs)
        print(f"{o:9s} {len(cs)} cases, {real} real, {len(cs) - real} placeholder")
    print(f"-> {', '.join(names)}, {len(out) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
