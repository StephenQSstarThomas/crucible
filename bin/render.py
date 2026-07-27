#!/usr/bin/env python3
"""Compile the paper and inspect the artifact a reviewer actually opens.

Checking .tex alone is not enough. A filled-in checklist that is commented out
in main.tex passes every source-level check and is simply absent from the PDF.
Everything here is measured on the compiled document.

Emits facts/render.json and preview/page-NN.png.
"""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

from crucible_lib import find_repo_and_root, run, write_json

OVERFULL_RX = re.compile(
    r"(Overfull|Underfull)\s+\\(hbox|vbox)\s*\(([\d.]+)pt too (wide|short)\)"
    r"(?:.*?(?:at lines?|in paragraph at lines?)\s+(\d+)(?:--(\d+))?)?",
    re.S)
UNDEF_REF_RX = re.compile(r"Reference\s+`([^']+)'\s+on page\s+(\d+)\s+undefined")
UNDEF_CITE_RX = re.compile(r"Citation\s+`([^']+)'\s+on page\s+(\d+)\s+undefined")
MISSING_FILE_RX = re.compile(r"(?:File|Package \w+ Error:.*?file)\s+`?([^'\s]+)'?\s+not found",
                             re.I)
LATEX_ERR_RX = re.compile(r"^! (.+)$", re.M)
BADBOX_PAGE_RX = re.compile(r"\[(\d+)\]")


def compile_pdf(repo: Path, root: Path, workdir: Path) -> dict:
    """Compile with tectonic into an isolated dir so the repo stays clean."""
    workdir.mkdir(parents=True, exist_ok=True)
    tectonic = shutil.which("tectonic")
    if not tectonic:
        return {"ok": False, "engine": None,
                "error": "tectonic not found on PATH"}

    # continue-on-errors matters: tectonic halts on *recoverable* errors by
    # default, so one pdftex-only microtype call in a .cls yields no PDF at
    # all. We still want the artifact, and we record the error separately.
    base = [tectonic, "-X", "compile", str(root),
            "--outdir", str(workdir), "--keep-logs", "--keep-intermediates",
            "--untrusted"]
    attempts = [
        base + ["-Z", "continue-on-errors"],
        base,
        [tectonic, str(root), "--outdir", str(workdir),
         "--keep-logs", "--keep-intermediates", "-Z", "continue-on-errors"],
        [tectonic, str(root), "--outdir", str(workdir),
         "--keep-logs", "--keep-intermediates"],
    ]
    rc, so, se = 1, "", ""
    used = None
    for cmd in attempts:
        rc, so, se = run(cmd, cwd=repo, timeout=900)
        used = cmd
        if (workdir / (root.stem + ".pdf")).is_file():
            break

    log = ""
    for cand in (workdir / (root.stem + ".log"), workdir / "texput.log"):
        if cand.is_file():
            log = cand.read_text(encoding="utf-8", errors="replace")
            break
    if not log:
        log = so + "\n" + se

    pdf = workdir / (root.stem + ".pdf")
    return {"ok": pdf.is_file(), "clean_exit": rc == 0, "returncode": rc,
            "engine": "tectonic (XeTeX)", "cmd": " ".join(used or []),
            "pdf": str(pdf) if pdf.is_file() else None,
            "log": log, "stderr": se[-8000:], "stdout": so[-4000:]}


def parse_log(log: str) -> dict:
    bad = []
    for m in OVERFULL_RX.finditer(log):
        bad.append({
            "kind": m.group(1).lower(), "box": m.group(2),
            "amount_pt": float(m.group(3)), "direction": m.group(4),
            "line_from": int(m.group(5)) if m.group(5) else None,
            "line_to": int(m.group(6)) if m.group(6) else None,
        })
    return {
        "badboxes": bad,
        "overfull_hbox_gt_5pt": [b for b in bad
                                 if b["kind"] == "overfull"
                                 and b["box"] == "hbox"
                                 and b["amount_pt"] > 5.0],
        "undefined_refs": [{"key": m.group(1), "page": int(m.group(2))}
                           for m in UNDEF_REF_RX.finditer(log)],
        "undefined_cites": [{"key": m.group(1), "page": int(m.group(2))}
                            for m in UNDEF_CITE_RX.finditer(log)],
        "missing_files": sorted({m.group(1)
                                 for m in MISSING_FILE_RX.finditer(log)}),
        "errors": [m.group(1).strip() for m in LATEX_ERR_RX.finditer(log)],
        "warnings_count": log.count("Warning:"),
    }


DRAFT_IN_PDF = ["TODO", "FIXME", "XXX", "PLACEHOLDER", "lorem ipsum",
                "Lorem ipsum", "TBD", "\\todo", "??"]


def inspect_pdf(pdf: Path, preview_dir: Path, dpi: int = 110) -> dict:
    try:
        import fitz
    except ImportError:
        return {"error": "pymupdf not installed"}

    doc = fitz.open(pdf)
    preview_dir.mkdir(parents=True, exist_ok=True)

    pages, full_text = [], []
    ref_start_page = None
    appendix_start_page = [None]
    for i, page in enumerate(doc, start=1):
        text = page.get_text()
        full_text.append(text)

        pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY)
        buf = pix.samples
        dark = sum(1 for b in buf if b < 200)
        coverage = dark / max(1, len(buf))

        pix_rgb = page.get_pixmap(dpi=dpi)
        pix_rgb.save(preview_dir / f"page-{i:02d}.png")

        # The heading can appear anywhere on the page, not just at the top:
        # a short Conclusion often leaves References starting mid-page.
        if ref_start_page is None and i > 1 and re.search(
                r"^[ \t]*(References|Bibliography|REFERENCES)[ \t]*$",
                text, re.M):
            ref_start_page = i
        if appendix_start_page[0] is None and i > 1 and re.search(
                r"^[ \t]*(Appendix|APPENDIX|Appendices|"
                r"Supplementary Material)[ \t]*$", text, re.M):
            appendix_start_page[0] = i

        pages.append({
            "page": i,
            "width_pt": round(page.rect.width, 2),
            "height_pt": round(page.rect.height, 2),
            "chars": len(text),
            "ink_coverage": round(coverage, 5),
            "mostly_empty": coverage < 0.015,
            "image_count": len(page.get_images(full=True)),
            "png": f"preview/page-{i:02d}.png",
            "first_line": (text.strip().splitlines() or [""])[0][:120],
        })

    joined = "\n".join(full_text)
    leaked = []
    for mk in DRAFT_IN_PDF:
        for m in re.finditer(re.escape(mk), joined):
            ctx = joined[max(0, m.start() - 60):m.end() + 60].replace("\n", " ")
            page_no = 1 + sum(1 for k in range(len(full_text))
                              if sum(len(t) + 1 for t in full_text[:k + 1]) <= m.start())
            leaked.append({"marker": mk, "page": page_no,
                           "context": re.sub(r"\s+", " ", ctx)})

    out = {
        "n_pages": len(pages),
        "pages": pages,
        "references_start_page": ref_start_page,
        "appendix_start_page": appendix_start_page[0],
        # Venues count "content pages" as main text + figures + tables, up to
        # where References begins. References itself starting mid-page means
        # that page is still partly content, so we count it.
        "content_pages_estimate": ref_start_page if ref_start_page
                                  else len(pages),
        "draft_markers_in_pdf": leaked,
        "empty_pages": [p["page"] for p in pages if p["mostly_empty"]],
        "metadata": dict(doc.metadata or {}),
        "text_by_page": [t[:20000] for t in full_text],
    }
    doc.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("-o", "--out", default="crucible-out")
    ap.add_argument("--root")
    ap.add_argument("--dpi", type=int, default=110)
    args = ap.parse_args()

    repo, root = find_repo_and_root(args.target)
    if args.root:
        root = (repo / args.root).resolve()

    outdir = Path(args.out)
    build = compile_pdf(repo, root, outdir / "build")

    result = {"root_tex": str(root.relative_to(repo)),
              "compiled": build["ok"],
              "clean_exit": build.get("clean_exit"),
              "engine": build.get("engine"),
              "cmd": build.get("cmd"),
              "returncode": build.get("returncode"),
              "compile_error": build.get("error")}

    if build.get("log"):
        result["log_analysis"] = parse_log(build["log"])
        (outdir / "build").mkdir(parents=True, exist_ok=True)
        (outdir / "build" / "compile.log").write_text(
            build["log"], encoding="utf-8")

    if build["ok"]:
        result["pdf"] = inspect_pdf(Path(build["pdf"]),
                                    outdir / "preview", args.dpi)
    else:
        result["stderr_tail"] = build.get("stderr", "")[-3000:]

    write_json(outdir / "facts" / "render.json", result)

    print(f"render: compiled={result['compiled']} "
          f"clean_exit={result.get('clean_exit')} "
          f"engine={result.get('engine')}")
    if result["compiled"] and not result.get("clean_exit"):
        print("  ! PDF produced only with continue-on-errors; "
              "the document has recoverable errors:")
        for e in (result.get("log_analysis", {}).get("errors") or [])[:4]:
            print(f"      ! {e[:150]}")
    if not result["compiled"]:
        print(f"  ! compile FAILED rc={result.get('returncode')}")
        for e in (result.get("log_analysis", {}).get("errors") or [])[:5]:
            print(f"      ! {e}")
        print((result.get("stderr_tail") or "")[-1200:])
        return

    pdf = result["pdf"]
    la = result["log_analysis"]
    print(f"  pages={pdf['n_pages']} "
          f"content_pages~{pdf['content_pages_estimate']} "
          f"(References p{pdf['references_start_page']}, "
          f"Appendix p{pdf['appendix_start_page']})")
    print(f"  overfull hbox >5pt: {len(la['overfull_hbox_gt_5pt'])} "
          f"| undefined refs: {len(la['undefined_refs'])} "
          f"| undefined cites: {len(la['undefined_cites'])} "
          f"| errors: {len(la['errors'])}")
    if pdf["draft_markers_in_pdf"]:
        print(f"  ! {len(pdf['draft_markers_in_pdf'])} draft marker(s) "
              f"VISIBLE IN THE PDF:")
        for d in pdf["draft_markers_in_pdf"][:8]:
            print(f"      p{d['page']} [{d['marker']}] {d['context'][:90]}")
    if pdf["empty_pages"]:
        print(f"  ! near-empty pages: {pdf['empty_pages']}")


if __name__ == "__main__":
    main()
