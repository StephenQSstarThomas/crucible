#!/usr/bin/env python3
"""Cross-reference integrity: cites vs bib, refs vs labels, orphan floats.

Both directions matter. Undefined keys break the build; unused entries and
never-referenced floats are softer but real reviewer irritants (B2.6, B2.7).

Emits facts/refs.json.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from crucible_lib import (collect_macros, find_repo_and_root, flatten,
                          load_json, write_json)

BIB_ENTRY_RX = re.compile(r"^\s*@(\w+)\s*\{\s*([^,\s]+)\s*,", re.M)


def parse_bib(repo: Path) -> dict:
    entries, files = {}, []
    for bib in sorted(repo.rglob("*.bib")):
        if any(p.startswith(".") for p in bib.parts):
            continue
        files.append(str(bib.relative_to(repo)))
        text = bib.read_text(encoding="utf-8", errors="replace")
        for m in BIB_ENTRY_RX.finditer(text):
            kind, key = m.group(1).lower(), m.group(2)
            # pull the entry body for later metadata verification
            start = m.end()
            depth, i = 1, start
            while i < len(text) and depth > 0:
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                i += 1
            body = text[start:i - 1]
            fields = {}
            for fm in re.finditer(r"(\w+)\s*=\s*[{\"](.*?)[}\"]\s*,?\s*(?=\w+\s*=|\Z)",
                                  body, re.DOTALL):
                fields[fm.group(1).lower()] = re.sub(
                    r"\s+", " ", fm.group(2)).strip()
            line = text[:m.start()].count("\n") + 1
            if key in entries:
                entries[key].setdefault("duplicates", []).append(
                    {"file": str(bib.relative_to(repo)), "line": line})
            else:
                entries[key] = {"key": key, "type": kind, "fields": fields,
                                "file": str(bib.relative_to(repo)),
                                "line": line}
    return {"files": files, "entries": entries}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("-o", "--out", default="crucible-out")
    ap.add_argument("--root")
    args = ap.parse_args()

    repo, root = find_repo_and_root(args.target)
    if args.root:
        root = (repo / args.root).resolve()

    facts = Path(args.out) / "facts"
    ing = load_json(facts / "ingest.json")

    labels = ing["labels"]
    keyval_labels = ing.get("keyval_labels", [])
    refs = ing["refs"]
    cites = ing["cites"]
    floats = ing["floats"]

    label_keys = {}
    dup_labels = []
    for l in labels:
        if l["key"] in label_keys:
            dup_labels.append({"key": l["key"], "first": label_keys[l["key"]],
                               "again": {"file": l["file"], "line": l["line"]}})
        else:
            label_keys[l["key"]] = {"file": l["file"], "line": l["line"]}

    keyval_keys = {k["key"]: {"file": k["file"], "line": k["line"]}
                   for k in keyval_labels}

    undefined_refs = [r for r in refs
                      if r["key"] not in label_keys and r["key"] not in keyval_keys]
    # Resolved only by a key-value option -- real, but worth surfacing since
    # whether it compiles depends on the package providing it.
    keyval_only_refs = [
        {**r, "defined_at": keyval_keys[r["key"]]}
        for r in refs if r["key"] not in label_keys and r["key"] in keyval_keys]

    ref_keys = {r["key"] for r in refs}
    unreferenced_labels = [
        l for l in labels if l["key"] not in ref_keys
        and not l["key"].startswith(("eq:", "app:sub"))
    ]
    all_label_keys = set(label_keys) | set(keyval_keys)

    bib = parse_bib(repo)
    bib_keys = set(bib["entries"])
    cite_keys = {c["key"] for c in cites}

    undefined_cites = [c for c in cites if c["key"] not in bib_keys]
    uncited_entries = sorted(bib_keys - cite_keys)

    # a float nobody points at reads as padding to a reviewer (B2.6)
    orphan_floats = []
    for f in floats:
        if not f["labels"]:
            orphan_floats.append({**{k: f[k] for k in
                                     ("env", "file", "line", "caption")},
                                  "reason": "no \\label at all"})
            continue
        if not any(lb in ref_keys for lb in f["labels"]):
            orphan_floats.append({**{k: f[k] for k in
                                     ("env", "file", "line", "caption")},
                                  "labels": f["labels"],
                                  "reason": "labelled but never \\ref'd"})

    # graphics files actually resolvable on disk (case-sensitive, B5.4)
    graphicspath = []
    for l in flatten(root, repo).lines:
        m = re.search(r"\\graphicspath\s*\{(.*)\}", l.code)
        if m:
            graphicspath = re.findall(r"\{([^}]*)\}", m.group(1))
    float_span = {}
    for f in floats:
        for g in f["graphics"]:
            float_span[g["path"]] = f["labels"]

    missing_graphics, found_graphics = [], []
    for g in ing.get("graphics_all", []):
        p = g["path"]
        cands = [repo / p]
        for gp in graphicspath:
            cands.append(repo / gp / p)
        for ext in (".pdf", ".png", ".jpg", ".jpeg", ".eps"):
            cands.append(repo / (p + ext))
            for gp in graphicspath:
                cands.append(repo / gp / (p + ext))
        hit = next((c for c in cands if c.is_file()), None)
        rec = {"path": p, "file": g["file"], "line": g["line"],
               "opts": g["opts"], "in_float": p in float_span,
               "float_labels": float_span.get(p, [])}
        if hit:
            found_graphics.append({**rec,
                                   "resolved": str(hit.relative_to(repo)),
                                   "bytes": hit.stat().st_size})
        else:
            missing_graphics.append(rec)

    # image files sitting in the repo that no \includegraphics uses
    used = {g["resolved"] for g in found_graphics}
    unused_images = []
    for img in sorted(repo.rglob("*")):
        if img.suffix.lower() not in (".png", ".jpg", ".jpeg", ".pdf", ".eps"):
            continue
        if any(part.startswith(".") for part in img.parts):
            continue
        rel = str(img.relative_to(repo))
        if rel not in used and "/" in rel:
            unused_images.append({"path": rel,
                                  "bytes": img.stat().st_size})

    out = {
        "n_labels": len(labels), "n_refs": len(refs), "n_cites": len(cites),
        "bib_files": bib["files"], "n_bib_entries": len(bib_keys),
        "duplicate_labels": dup_labels,
        "undefined_refs": undefined_refs,
        "keyval_only_refs": keyval_only_refs,
        "unreferenced_labels": unreferenced_labels,
        "undefined_cites": undefined_cites,
        "uncited_bib_entries": uncited_entries,
        "duplicate_bib_keys": [
            {"key": k, "duplicates": v["duplicates"]}
            for k, v in bib["entries"].items() if v.get("duplicates")],
        "orphan_floats": orphan_floats,
        "graphicspath": graphicspath,
        "graphics_found": found_graphics,
        "graphics_missing": missing_graphics,
        "unused_image_files": unused_images,
        "bib_entries": bib["entries"],
    }
    write_json(facts / "refs.json", out)

    print(f"refs: labels={len(labels)} refs={len(refs)} cites={len(cites)} "
          f"bib={len(bib_keys)}")
    for name, val in (("undefined \\ref", undefined_refs),
                      ("undefined \\cite", undefined_cites),
                      ("duplicate labels", dup_labels),
                      ("missing graphics", missing_graphics),
                      ("orphan floats", orphan_floats)):
        if val:
            print(f"  ! {name}: {len(val)}")
            for v in val[:5]:
                print(f"      {v.get('key') or v.get('path') or v.get('caption','')[:50]}"
                      f"  ({v.get('file')}:{v.get('line')})")
    print(f"  . uncited bib entries: {len(uncited_entries)}")


if __name__ == "__main__":
    main()
