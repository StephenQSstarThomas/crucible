#!/usr/bin/env python3
"""Venue conformance -- deliberately the LAST tier (Axiom 1).

Venue rules expire; correctness does not. Keeping these checks separate means
retargeting a paper from NeurIPS to ICML invalidates only this tier's findings.

Emits facts/venue.json.
"""
from __future__ import annotations

import argparse
import hashlib
import re
from datetime import date, datetime
from pathlib import Path

import yaml

from crucible_lib import (collect_macros, find_repo_and_root, flatten,
                          load_json, to_prose, write_json)

VENUE_DIR = Path(__file__).resolve().parent.parent / "venues"

SECTIONING = r"\\(?:part|chapter|section|subsection|subsubsection|paragraph)\b"
NEG_VSPACE = re.compile(r"\\vspace\*?\s*\{\s*-\s*([\d.]+)\s*(em|ex|pt|in|cm|mm|baselineskip)\s*\}")

GEOMETRY_HACKS = [
    r"\\setlength\s*\{\s*\\(textwidth|textheight|oddsidemargin|evensidemargin"
    r"|topmargin|footskip|headsep|headheight|parskip|parindent|baselineskip"
    r"|columnsep|floatsep|textfloatsep|intextsep|abovedisplayskip"
    r"|belowdisplayskip)\s*\}",
    r"\\addtolength\s*\{\s*\\(textwidth|textheight|oddsidemargin|topmargin"
    r"|parskip|baselineskip)\s*\}",
    r"\\usepackage\s*(\[[^\]]*\])?\s*\{geometry\}",
    r"\\geometry\s*\{",
    r"\\renewcommand\s*\{?\s*\\baselinestretch",
    r"\\linespread\s*\{",
    r"\\fontsize\s*\{",
]

IDENTITY_PATTERNS = [
    ("email", r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
    # Grouped contact lines are written as \{a,b,c\}@inst.edu, so the local
    # part is braces and the plain email pattern never fires.
    ("email_grouped", r"\\?\{[A-Za-z0-9._,\s\\]+\\?\}\s*@\s*[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
    ("email_texttt", r"\\texttt\s*\{[^}]*@[^}]*\}"),
    ("github", r"github\.com/[A-Za-z0-9_\-]+"),
    ("gitlab", r"gitlab\.com/[A-Za-z0-9_\-]+"),
    ("huggingface", r"huggingface\.co/[A-Za-z0-9_\-]+"),
    ("personal_site", r"https?://(?:www\.)?[A-Za-z0-9\-]+\.(?:io|me|ai|com)/~?[A-Za-z]+"),
    ("orcid", r"orcid\.org/[\d\-X]+"),
]

SELF_REF = re.compile(
    r"\b(our (?:previous|prior|earlier|recent) (?:work|paper|study|system)|"
    r"we (?:previously|earlier) (?:showed|proposed|introduced|presented)|"
    r"in our (?:previous|prior|earlier) )", re.I)

ACK_RX = re.compile(r"\\(?:section|subsection)\*?\s*\{\s*Acknowledg",
                    re.I)


def load_venue(slug: str) -> dict:
    p = VENUE_DIR / f"{slug}.yaml"
    if not p.is_file():
        raise SystemExit(f"crucible: unknown venue '{slug}'. "
                         f"Available: {[q.stem for q in VENUE_DIR.glob('*.yaml')]}")
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def check_style_tampering(doc, ing) -> dict:
    """Systematic negative vspace next to sectioning is the classic squeeze."""
    neg = []
    for l in doc.lines:
        if l.in_verbatim:
            continue
        for m in NEG_VSPACE.finditer(l.code):
            window_lo = max(0, l.vline - 3)
            window = "\n".join(x.code for x in doc.lines[window_lo:l.vline + 2])
            neg.append({
                "file": l.file, "line": l.lineno,
                "amount": f"-{m.group(1)}{m.group(2)}",
                "near_sectioning": bool(re.search(SECTIONING, window)),
                "text": l.code.strip()[:120],
            })
    geom = []
    for l in doc.lines:
        if l.in_verbatim:
            continue
        for pat in GEOMETRY_HACKS:
            for m in re.finditer(pat, l.code):
                geom.append({"file": l.file, "line": l.lineno,
                             "match": m.group(0)[:80],
                             "text": l.code.strip()[:120]})
    by_file = {}
    for n in neg:
        by_file.setdefault(n["file"], 0)
        by_file[n["file"]] += 1
    return {
        "negative_vspace_total": len(neg),
        "negative_vspace_near_sectioning": sum(1 for n in neg
                                               if n["near_sectioning"]),
        "negative_vspace_by_file": by_file,
        "negative_vspace": neg,
        "geometry_modifications": geom,
    }


def scan_forbidden_options(repo: Path, roots: list[str],
                           forbidden: list[str]) -> list[dict]:
    """Scan EVERY candidate main file, not just the compiled one.

    A repo can carry main.tex (compiled here) and main-nips.tex (the file
    actually submitted). The de-anonymizing option often sits in the one we
    did not compile, so scanning only the compiled tree misses it entirely.
    """
    out = []
    for r in roots:
        p = repo / r
        if not p.is_file():
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8",
                                             errors="replace").splitlines(), 1):
            code = line.split("%")[0] if not line.strip().startswith("%") else ""
            for m in re.finditer(
                    r"\\(?:usepackage|documentclass)\s*\[([^\]]*)\]\s*\{([^}]*)\}",
                    code):
                opts = [o.strip() for o in m.group(1).split(",")]
                for f in forbidden:
                    if f in opts:
                        out.append({"option": f, "package": m.group(2).strip(),
                                    "file": r, "line": i,
                                    "text": line.strip()[:140]})
    return out


def check_anonymity(doc, ing, render, venue) -> dict:
    text = doc.text()
    hits = []
    for name, pat in IDENTITY_PATTERNS:
        for l in doc.lines:
            if l.in_verbatim:
                continue
            for m in re.finditer(pat, l.code):
                hits.append({"kind": name, "match": m.group(0)[:120],
                             "file": l.file, "line": l.lineno})

    authors = []
    for l in doc.lines:
        for m in re.finditer(r"\\author\s*(\[[^\]]*\])?\s*\{([^}]*)\}", l.code):
            authors.append({"name": m.group(2).strip(), "file": l.file,
                            "line": l.lineno})
    affils = []
    for l in doc.lines:
        for m in re.finditer(r"\\(?:affiliation|institute|affil)\s*(\[[^\]]*\])?\s*\{([^}]*)\}",
                             l.code):
            affils.append({"name": m.group(2).strip()[:120], "file": l.file,
                           "line": l.lineno})

    forbidden = venue.get("forbidden_class_options", []) or []
    bad_opts = []
    for l in doc.lines:
        for m in re.finditer(
                r"\\usepackage\s*\[([^\]]*)\]\s*\{([^}]*)\}", l.code):
            opts = [o.strip() for o in m.group(1).split(",")]
            pkgs = [p.strip() for p in m.group(2).split(",")]
            for f in forbidden:
                if f in opts:
                    bad_opts.append({"option": f, "package": ",".join(pkgs),
                                     "file": l.file, "line": l.lineno,
                                     "text": l.code.strip()[:140]})
        m = re.search(r"\\documentclass\s*\[([^\]]*)\]", l.code)
        if m:
            for f in forbidden:
                if f in [o.strip() for o in m.group(1).split(",")]:
                    bad_opts.append({"option": f, "package": "documentclass",
                                     "file": l.file, "line": l.lineno,
                                     "text": l.code.strip()[:140]})

    ack = [{"file": l.file, "line": l.lineno}
           for l in doc.lines if ACK_RX.search(l.code)]
    selfref = [{"file": l.file, "line": l.lineno, "match": m.group(0)}
               for l in doc.lines for m in [SELF_REF.search(l.code)] if m]

    pdf_meta = (render.get("pdf") or {}).get("metadata", {}) or {}
    meta_leak = {k: v for k, v in pdf_meta.items()
                 if k.lower() in ("author", "creator", "producer", "title")
                 and v and str(v).strip()}

    return {
        "forbidden_class_options": bad_opts,
        "authors_declared": authors,
        "affiliations_declared": affils,
        "identity_strings": hits,
        "acknowledgments_sections": ack,
        "first_person_self_reference": selfref,
        "pdf_metadata": meta_leak,
    }


def check_required_material(doc, ing, render, venue) -> dict:
    """Presence is judged on the COMPILED PDF, not the source tree."""
    pdf_text = "\n".join((render.get("pdf") or {}).get("text_by_page", []))
    out = {}

    if venue.get("checklist_required"):
        src_has = any("checklist" in f.lower() for f in ing["files"])
        commented = [c for c in ing.get("commented_out_inputs", [])
                     if "checklist" in c["target"].lower()]
        pdf_has = bool(re.search(
            r"(NeurIPS Paper Checklist|Paper Checklist|"
            r"Claims\s*\n?\s*Question:|Answer:\s*\[?Yes)", pdf_text, re.I))
        out["checklist"] = {
            "required": True,
            "source_file_present": src_has,
            "commented_out_inputs": commented,
            "present_in_pdf": pdf_has,
            "verdict": "present" if pdf_has else
                       ("file_exists_but_not_included" if (src_has or commented)
                        else "absent"),
        }

    for key, label, pat in (
            ("limitations_required", "limitations",
             r"^\s*\d*\.?\s*Limitations?\s*$|\\section\*?\{\s*Limitations"),
            ("broader_impact_required", "broader_impact",
             r"Broader Impact|Societal Impact|Ethics Statement|"
             r"Ethical Considerations")):
        if venue.get(key):
            in_pdf = bool(re.search(pat, pdf_text, re.M | re.I))
            in_src = bool(re.search(pat, doc.text(), re.M | re.I))
            out[label] = {"required": True, "present_in_pdf": in_pdf,
                          "present_in_source": in_src}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("-o", "--out", default="crucible-out")
    ap.add_argument("--venue", required=True)
    ap.add_argument("--root")
    ap.add_argument("--double-blind", choices=["auto", "yes", "no"],
                    default="auto",
                    help="submission is anonymous. 'no' for camera-ready/preprint")
    args = ap.parse_args()

    repo, root = find_repo_and_root(args.target)
    if args.root:
        root = (repo / args.root).resolve()

    facts = Path(args.out) / "facts"
    ing = load_json(facts / "ingest.json")
    render = load_json(facts / "render.json") if (facts / "render.json").is_file() else {}
    venue = load_venue(args.venue)
    doc = flatten(root, repo)

    dbl = venue.get("double_blind", False)
    if args.double_blind == "yes":
        dbl = True
    elif args.double_blind == "no":
        dbl = False

    content_pages = (render.get("pdf") or {}).get("content_pages_estimate")
    limit = venue.get("content_pages")

    # staleness: rules we have not re-verified recently are advisory only
    stale = None
    if venue.get("verified_on"):
        v = venue["verified_on"]
        v = v if isinstance(v, date) else datetime.fromisoformat(str(v)).date()
        age = (date.today() - v).days
        stale = {"verified_on": str(v), "age_days": age,
                 "is_stale": age > int(venue.get("staleness_warning_after_days",
                                                 180))}

    style_file = venue.get("required_style_file")
    style_info = None
    if style_file:
        hits = list(repo.rglob(style_file))
        if hits:
            h = hashlib.sha256(hits[0].read_bytes()).hexdigest()
            style_info = {"present": True,
                          "path": str(hits[0].relative_to(repo)),
                          "sha256": h, "bytes": hits[0].stat().st_size}
        else:
            style_info = {"present": False}

    # is the root we compiled even the one that uses the venue template?
    roots = ing["all_documentclass_files"]
    uses_venue_style = []
    for r in roots:
        txt = (repo / r).read_text(encoding="utf-8", errors="replace")
        uses_venue_style.append({
            "file": r,
            "uses_required_style": bool(style_file and
                                        re.search(re.escape(style_file.replace(".sty", "")),
                                                  txt)),
            "documentclass": (re.search(r"\\documentclass\s*(\[[^\]]*\])?\s*\{([^}]*)\}",
                                        txt).group(2)
                              if re.search(r"\\documentclass", txt) else None),
        })

    out = {
        "venue": venue.get("slug"), "venue_name": venue.get("name"),
        "rules_staleness": stale,
        "double_blind_assumed": dbl,
        "double_blind_source": args.double_blind,
        "root_compiled": str(root.relative_to(repo)),
        "candidate_roots": uses_venue_style,
        "multiple_roots": len(roots) > 1,
        "page_limit": {
            "limit": limit, "content_pages_estimate": content_pages,
            "total_pages": (render.get("pdf") or {}).get("n_pages"),
            "references_start_page": (render.get("pdf") or {}).get("references_start_page"),
            "over_limit": (content_pages is not None and limit is not None
                           and content_pages > limit),
            "margin": (limit - content_pages)
                      if (content_pages is not None and limit is not None) else None,
        },
        "style_file": style_info,
        "style_tampering": check_style_tampering(doc, ing),
        "required_material": check_required_material(doc, ing, render, venue),
    }
    if dbl:
        out["anonymity"] = check_anonymity(doc, ing, render, venue)
        out["anonymity"]["forbidden_class_options_all_roots"] = \
            scan_forbidden_options(repo, roots,
                                   venue.get("forbidden_class_options") or [])

    write_json(facts / "venue.json", out)

    pl = out["page_limit"]
    print(f"venue: {venue.get('name')}  (double_blind={dbl})")
    if stale and stale["is_stale"]:
        print(f"  ! venue rules last verified {stale['verified_on']} "
              f"({stale['age_days']}d ago) -- re-check the official site")
    print(f"  pages: content~{pl['content_pages_estimate']} / limit {pl['limit']}"
          f"  {'OVER LIMIT' if pl['over_limit'] else 'ok'}")
    if out["multiple_roots"]:
        print(f"  ! {len(roots)} candidate main files:")
        for r in uses_venue_style:
            print(f"      {r['file']:22s} class={r['documentclass']:14s} "
                  f"uses {style_file}={r['uses_required_style']}")
    st = out["style_tampering"]
    if st["negative_vspace_total"]:
        print(f"  ! negative \\vspace: {st['negative_vspace_total']} total, "
              f"{st['negative_vspace_near_sectioning']} adjacent to sectioning")
        print(f"      by file: {st['negative_vspace_by_file']}")
    if st["geometry_modifications"]:
        print(f"  ! geometry/font modifications: "
              f"{len(st['geometry_modifications'])}")
    rm = out["required_material"]
    if "checklist" in rm:
        c = rm["checklist"]
        print(f"  checklist: {c['verdict']}  "
              f"(source_file={c['source_file_present']}, in_pdf={c['present_in_pdf']})")
        for cc in c["commented_out_inputs"]:
            print(f"      ! commented out at {cc['file']}:{cc['line']} "
                  f"-> {cc['target']} ({cc['target_bytes']} bytes, filled in)")
    for k in ("limitations", "broader_impact"):
        if k in rm:
            print(f"  {k}: in_pdf={rm[k]['present_in_pdf']}")
    if dbl:
        an = out["anonymity"]
        allb = an.get("forbidden_class_options_all_roots") or []
        if allb:
            print(f"  ! FORBIDDEN OPTION (de-anonymizes) in {len(allb)} place(s):")
            for b in allb:
                print(f"      {b['file']}:{b['line']}  [{b['option']}] "
                      f"{b['text']}")
        if an["authors_declared"]:
            print(f"  ! {len(an['authors_declared'])} \\author declarations")
        if an["affiliations_declared"]:
            print(f"  ! {len(an['affiliations_declared'])} affiliations")
        if an["identity_strings"]:
            kinds = {}
            for h in an["identity_strings"]:
                kinds[h["kind"]] = kinds.get(h["kind"], 0) + 1
            print(f"  ! identity strings: {kinds}")
            for h in an["identity_strings"][:5]:
                print(f"      {h['file']}:{h['line']}  [{h['kind']}] {h['match']}")


if __name__ == "__main__":
    main()
