#!/usr/bin/env python3
"""Audit figures at the size they are actually printed.

The common mistake is judging a figure by its source file: a 3000px-wide PNG
looks sharp until it is placed at 0.9\\linewidth, where it is ~5in across and
its 10pt labels render under 4pt. Effective DPI is measured from the PLACED
rectangle in the compiled PDF, and a high-res crop of each figure is written
out so an agent can look at it directly.

Emits facts/figures.json and figures/fig-NN.png crops.
"""
from __future__ import annotations

import argparse
import math
import re
from collections import defaultdict
from pathlib import Path

from crucible_lib import find_repo_and_root, load_json, write_json

# Matrices from Viénot/Brettel-style LMS simulation, applied in linear RGB.
CVD_MATRICES = {
    "deuteranopia": [[0.625, 0.375, 0.0], [0.7, 0.3, 0.0], [0.0, 0.3, 0.7]],
    "protanopia":   [[0.567, 0.433, 0.0], [0.558, 0.442, 0.0], [0.0, 0.242, 0.758]],
    "tritanopia":   [[0.95, 0.05, 0.0], [0.0, 0.433, 0.567], [0.0, 0.475, 0.525]],
}


def phash(img, size: int = 16) -> str:
    """Average-hash for near-duplicate figure detection (I6.1/I6.2)."""
    g = img.convert("L").resize((size, size))
    px = list(g.tobytes())          # mode "L" -> one byte per pixel
    avg = sum(px) / len(px)
    bits = "".join("1" if p > avg else "0" for p in px)
    return f"{int(bits, 2):0{size * size // 4}x}"


def hamming(a: str, b: str) -> int:
    if len(a) != len(b):
        return 10 ** 6
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def simulate_cvd(img, kind: str):
    from PIL import Image
    m = CVD_MATRICES[kind]
    rgb = img.convert("RGB")
    return rgb.convert("RGB", (
        m[0][0], m[0][1], m[0][2], 0,
        m[1][0], m[1][1], m[1][2], 0,
        m[2][0], m[2][1], m[2][2], 0,
    ))


def palette_signature(img, n: int = 6) -> list[tuple[str, float]]:
    """Dominant saturated colours; these are what encode data series."""
    from PIL import Image
    small = img.convert("RGB").resize((120, 120))
    counts = defaultdict(int)
    total = 0
    raw = small.tobytes()           # mode "RGB" -> three bytes per pixel
    for r, g, b in zip(raw[0::3], raw[1::3], raw[2::3]):
        mx, mn = max(r, g, b), min(r, g, b)
        if mx < 40 or mx - mn < 45:      # ignore black/white/grey structure
            continue
        counts[(r // 40 * 40, g // 40 * 40, b // 40 * 40)] += 1
        total += 1
    if not total:
        return []
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:n]
    return [(f"#{r:02x}{g:02x}{b:02x}", round(c / total, 4))
            for (r, g, b), c in top]


def redgreen_risk(sig) -> dict:
    """Flag red-vs-green as the only distinction (F3.1)."""
    reds = greens = 0.0
    for hexs, frac in sig:
        r = int(hexs[1:3], 16)
        g = int(hexs[3:5], 16)
        b = int(hexs[5:7], 16)
        if r > g + 40 and r > b + 40:
            reds += frac
        if g > r + 40 and g > b + 25:
            greens += frac
    return {"red_share": round(reds, 4), "green_share": round(greens, 4),
            "both_present": reds > 0.08 and greens > 0.08}


def cvd_collapse(img) -> dict:
    """How much of the colour separation survives colour-vision deficiency."""
    base = palette_signature(img)
    out = {}
    for kind in CVD_MATRICES:
        try:
            sim = simulate_cvd(img, kind)
        except Exception:
            continue
        s = palette_signature(sim)
        out[kind] = {"distinct_colours_before": len(base),
                     "distinct_colours_after": len(s)}
    return out


def estimate_text_pt(crop_path: Path, crop_dpi: int) -> dict:
    """Estimate the smallest rendered text size in a raster figure.

    Effective DPI alone is not legibility. A screenshot pasted into a figure
    can measure 700+ dpi and still print at 1pt, because what matters is how
    large the glyphs are AFTER the whole figure is scaled into the column.

    Method: horizontal dark-pixel projection finds contiguous runs of ink
    rows; each run approximates one text line's cap height. The crop is
    rendered at a known dpi, so px -> points is exact.
    """
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        return {"available": False}
    try:
        a = np.array(Image.open(crop_path).convert("L"))
    except Exception as e:
        return {"available": False, "error": str(e)}

    H, W = a.shape
    dark = a < 128
    runs, cur = [], 0
    for v in dark.sum(axis=1):
        if v > max(2, W * 0.002):
            cur += 1
        elif cur:
            runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    runs = sorted(r for r in runs if 2 <= r <= H * 0.2)
    if not runs:
        return {"available": True, "n_text_lines": 0}

    def to_pt(px):
        return round(px / crop_dpi * 72.0, 2)

    med = runs[len(runs) // 2]
    p10 = runs[max(0, int(len(runs) * 0.10))]
    return {
        "available": True,
        "n_text_lines": len(runs),
        "min_line_pt": to_pt(runs[0]),
        "p10_line_pt": to_pt(p10),
        "median_line_pt": to_pt(med),
        "max_line_pt": to_pt(runs[-1]),
        # p10 rather than min: a single speck should not condemn a figure,
        # but if a tenth of all text lines are sub-6pt it is unreadable.
        "illegible": to_pt(p10) < 6.0,
        "severely_illegible": to_pt(med) < 4.0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("-o", "--out", default="crucible-out")
    ap.add_argument("--crop-dpi", type=int, default=300)
    args = ap.parse_args()

    repo, _ = find_repo_and_root(args.target)
    outdir = Path(args.out)
    facts = outdir / "facts"
    ing = load_json(facts / "ingest.json")
    refs = load_json(facts / "refs.json")

    try:
        from PIL import Image
    except ImportError:
        Image = None

    # ---- source-file properties -------------------------------------------
    sources = {}
    for g in refs["graphics_found"]:
        p = repo / g["resolved"]
        rec = {"path": g["path"], "resolved": g["resolved"],
               "bytes": g["bytes"], "opts": g["opts"],
               "file": g["file"], "line": g["line"],
               "format": p.suffix.lower().lstrip("."),
               "is_vector": p.suffix.lower() in (".pdf", ".eps", ".ps", ".svg")}
        if Image and not rec["is_vector"]:
            try:
                with Image.open(p) as im:
                    rec["px_width"], rec["px_height"] = im.size
                    rec["mode"] = im.mode
                    rec["phash"] = phash(im)
                    sig = palette_signature(im)
                    rec["palette"] = sig
                    rec["redgreen"] = redgreen_risk(sig)
                    rec["cvd"] = cvd_collapse(im)
            except Exception as e:
                rec["error"] = str(e)
        sources[g["resolved"]] = rec

    # ---- near-duplicate detection across figures --------------------------
    dupes = []
    keys = [k for k, v in sources.items() if v.get("phash")]
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = sources[keys[i]], sources[keys[j]]
            d = hamming(a["phash"], b["phash"])
            if d <= 12:
                dupes.append({"a": keys[i], "b": keys[j], "hamming": d,
                              "identical": d == 0})

    # ---- placed geometry from the compiled PDF ----------------------------
    placed = []
    render = {}
    rpath = facts / "render.json"
    if rpath.is_file():
        render = load_json(rpath)
    pdf_path = outdir / "build"
    pdfs = list(pdf_path.glob("*.pdf")) if pdf_path.is_dir() else []
    if pdfs and render.get("compiled"):
        try:
            import fitz
            doc = fitz.open(pdfs[0])
            cropdir = outdir / "figures"
            cropdir.mkdir(parents=True, exist_ok=True)
            n = 0
            for pno, page in enumerate(doc, start=1):
                for info in page.get_image_info(xrefs=True):
                    bbox = info.get("bbox")
                    if not bbox:
                        continue
                    w_pt = bbox[2] - bbox[0]
                    h_pt = bbox[3] - bbox[1]
                    if w_pt < 40 or h_pt < 20:      # logos, inline glyphs
                        continue
                    n += 1
                    px_w = info.get("width", 0)
                    px_h = info.get("height", 0)
                    eff_dpi_w = px_w / (w_pt / 72.0) if w_pt else 0
                    eff_dpi_h = px_h / (h_pt / 72.0) if h_pt else 0

                    crop_name = f"fig-{n:02d}_p{pno:02d}.png"
                    try:
                        clip = fitz.Rect(*bbox)
                        pm = page.get_pixmap(dpi=args.crop_dpi, clip=clip)
                        pm.save(cropdir / crop_name)
                    except Exception:
                        crop_name = None

                    # font sizes of any text drawn inside the figure rect --
                    # available for vector figures, absent for rasters
                    spans = []
                    try:
                        td = page.get_text("dict", clip=fitz.Rect(*bbox))
                        for blk in td.get("blocks", []):
                            for ln in blk.get("lines", []):
                                for sp in ln.get("spans", []):
                                    if sp.get("text", "").strip():
                                        spans.append(round(sp["size"], 2))
                    except Exception:
                        pass

                    measured = ({} if not crop_name else
                                estimate_text_pt(cropdir / crop_name,
                                                 args.crop_dpi))

                    placed.append({
                        "page": pno,
                        "bbox_pt": [round(v, 1) for v in bbox],
                        "width_pt": round(w_pt, 1), "height_pt": round(h_pt, 1),
                        "width_in": round(w_pt / 72.0, 3),
                        "px_width": px_w, "px_height": px_h,
                        "effective_dpi": round(min(eff_dpi_w, eff_dpi_h), 1),
                        "below_300dpi": min(eff_dpi_w, eff_dpi_h) < 300,
                        "text_layer_sizes_pt": sorted(set(spans))[:12],
                        "min_text_pt": min(spans) if spans else None,
                        "has_text_layer": bool(spans),
                        # for rasters this is the only legibility signal
                        "measured_text": measured,
                        "crop": f"figures/{crop_name}" if crop_name else None,
                    })
            doc.close()
        except ImportError:
            pass

    # ---- caption quality (F4) ---------------------------------------------
    captions = []
    for f in ing["floats"]:
        cap = f["caption_prose"]
        captions.append({
            "env": f["env"], "file": f["file"], "line": f["line"],
            "labels": f["labels"],
            "caption_words": len(cap.split()),
            "caption": cap[:400],
            "very_short": len(cap.split()) < 8,
            "mentions_n": bool(re.search(r"\b[Nn]\s*=|\bper\b|topics?\b|runs?\b",
                                         cap)),
            "mentions_errorbar": bool(re.search(
                r"error bar|std|standard deviation|confidence|CI\b|s\.e\.|sem\b",
                cap, re.I)),
            "explains_symbols": bool(re.search(
                r"\\ding|†|‡|\*|dagger|cross|check|mark", f["caption_raw"])),
        })

    out = {
        "sources": sources,
        "near_duplicate_pairs": dupes,
        "placed_images": placed,
        "n_placed": len(placed),
        "low_dpi_placed": [p for p in placed if p["below_300dpi"]],
        "small_text_placed": [p for p in placed
                              if p["min_text_pt"] and p["min_text_pt"] < 6.0],
        "illegible_raster_text": [
            p for p in placed
            if (p.get("measured_text") or {}).get("illegible")],
        "captions": captions,
    }
    write_json(facts / "figures.json", out)

    print(f"figures: {len(sources)} source file(s), {len(placed)} placed image(s)")
    for k, v in sources.items():
        if v.get("px_width"):
            print(f"  {k:52s} {v['px_width']}x{v['px_height']} "
                  f"{v['bytes']//1024:>5d}KB "
                  f"{'VECTOR' if v['is_vector'] else v['format'].upper()}")
    for p in placed:
        flag = "  <-- BELOW 300 DPI" if p["below_300dpi"] else ""
        print(f"  p{p['page']:>2d} placed {p['width_in']}in wide, "
              f"{p['px_width']}px -> {p['effective_dpi']} dpi{flag}")
        mt = p.get("measured_text") or {}
        if mt.get("n_text_lines"):
            mark = "  <-- ILLEGIBLE" if mt.get("illegible") else ""
            print(f"       text lines: {mt['n_text_lines']}, "
                  f"p10={mt['p10_line_pt']}pt median={mt['median_line_pt']}pt"
                  f"{mark}")
    if dupes:
        print(f"  ! {len(dupes)} near-duplicate figure pair(s):")
        for d in dupes:
            print(f"      {d['a']} ~ {d['b']} (hamming={d['hamming']})")
    for k, v in sources.items():
        rg = v.get("redgreen") or {}
        if rg.get("both_present"):
            print(f"  ! red/green both dominant in {k} "
                  f"(red={rg['red_share']}, green={rg['green_share']})")


if __name__ == "__main__":
    main()
