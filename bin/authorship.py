#!/usr/bin/env python3
"""Collect authorship-provenance facts without classifying the manuscript.

The three-way judgment (human-led / substantial AI involvement / fully AI)
belongs to the authorship assessor.  This collector only records direct
disclosures, high-specificity generation artifacts, revision traces, source
availability, lightweight section statistics, and version-control metadata.
Text style alone is deliberately treated as non-diagnostic.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from crucible_lib import (collect_macros, demacro, find_repo_and_root, flatten,
                          load_json, run, to_prose, write_json)


AI_TOOL_RX = re.compile(
    r"\b(ChatGPT|GPT-?[2345](?:\.\d+)?|Claude|Gemini|Copilot|DeepSeek|"
    r"large language model|LLM|generative AI|AI assistant)\b", re.I)

DISCLOSURE_TITLE_RX = re.compile(
    r"\b(AI|LLM|language model|generative AI)\b.*\b(use|usage|assistance|"
    r"disclosure|statement|declaration)|\b(use|usage|assistance|disclosure|"
    r"statement|declaration)\b.*\b(AI|LLM|language model|generative AI)\b",
    re.I)

WRITING_USE_RX = re.compile(
    r"(?:\b(?:we|the authors?)\b.{0,80}\b(?:used|employed|utili[sz]ed|"
    r"relied on)\b.{0,80}\b(?:ChatGPT|Claude|Gemini|Copilot|large language "
    r"models?|LLMs?|generative AI|AI assistants?)\b.{0,100}\b(?:writ|draft|"
    r"edit|revis|polish|proofread|language|text)|"
    r"\b(?:text|manuscript|paper|article|prose)\b.{0,80}\b(?:generated|"
    r"written|drafted|rewritten|edited|revised|polished|proofread)\b.{0,80}"
    r"\b(?:by|with|using)\b.{0,60}\b(?:ChatGPT|Claude|Gemini|Copilot|"
    r"large language models?|LLMs?|generative AI|AI assistants?)\b)",
    re.I)

FULL_GENERATION_RX = re.compile(
    r"\b(?:entire|full|complete|all(?: of)? the)\b.{0,45}"
    r"\b(?:manuscript|paper|article|text|prose|sections?)\b.{0,80}"
    r"\b(?:generated|written|drafted|produced)\b.{0,60}"
    r"\b(?:by|with|using)\b.{0,60}\b(?:AI|ChatGPT|Claude|Gemini|LLMs?|"
    r"language models?)\b|"
    r"\b(?:AI|ChatGPT|Claude|Gemini|LLMs?|language models?)\b.{0,60}"
    r"\b(?:generated|wrote|drafted|produced)\b.{0,80}"
    r"\b(?:entire|full|complete|all(?: of)? the)\b.{0,45}"
    r"\b(?:manuscript|paper|article|text|prose|sections?)\b",
    re.I)

WRITING_ACTIVITY_RX = re.compile(
    r"\b(?:manuscript|paper|article|prose|text|writ(?:e|ing|ten)|draft(?:ing|ed)?|"
    r"edit(?:ing|ed)?|revis(?:e|ing|ed|ion)|polish(?:ing|ed)?|proofread(?:ing)?)\b",
    re.I)

GENERATION_LEAKS = {
    "ai-self-reference": re.compile(
        r"\b(?:as an AI language model|as a language model|I (?:cannot|can't) "
        r"access|I do not have access to)\b", re.I),
    "chat-transcript-marker": re.compile(
        r"^\s*(?:Assistant|ChatGPT|Claude|User)\s*:\s+", re.I),
    "placeholder-citation": re.compile(
        r"\[(?:insert|add) (?:citation|reference)[^\]]*\]|"
        r"\((?:Author|Authors?)\s*,?\s*(?:Year|20XX)\)", re.I),
    "generation-instruction": re.compile(
        r"\b(?:here is (?:a|the) revised (?:paragraph|section)|"
        r"certainly[,!]? here (?:is|are)|I have rewritten)\b", re.I),
}

REVISION_COMMAND_RX = re.compile(
    r"\\(?:added|deleted|replaced|change|revise|todo|fixme|hl|marginpar)\b",
    re.I)


def snippets(pattern: re.Pattern, text: str, limit: int = 20) -> list[str]:
    out = []
    for match in pattern.finditer(text):
        lo = max(0, match.start() - 120)
        hi = min(len(text), match.end() + 180)
        out.append(re.sub(r"\s+", " ", text[lo:hi]).strip())
        if len(out) >= limit:
            break
    return out


def git_provenance(repo: Path) -> dict:
    if not (repo / ".git").exists():
        return {"available": False, "reason": "no .git directory"}
    rc, count, err = run(["git", "rev-list", "--count", "HEAD"], cwd=repo)
    if rc != 0:
        return {"available": False, "reason": err.strip()[:300]}
    _, authors, _ = run(
        ["git", "shortlog", "-sne", "HEAD"], cwd=repo)
    _, dates, _ = run(
        ["git", "log", "--reverse", "--format=%aI", "--", "*.tex"],
        cwd=repo)
    date_lines = [line.strip() for line in dates.splitlines() if line.strip()]
    return {
        "available": True,
        "commit_count": int(count.strip()),
        "author_entries": [line.strip() for line in authors.splitlines()
                           if line.strip()],
        "first_tex_commit": date_lines[0] if date_lines else None,
        "last_tex_commit": date_lines[-1] if date_lines else None,
        "note": "History can show revision activity but cannot identify who "
                "authored the prose or whether AI was used off-repository.",
    }


def section_stats(ing: dict) -> list[dict]:
    out = []
    for block in ing.get("prose_by_section", []):
        prose = block.get("prose", "")
        words = re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)*", prose)
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", prose.strip()) if s]
        out.append({
            "section": block.get("section"),
            "file": block.get("file"),
            "line": block.get("line"),
            "word_count": len(words),
            "sentence_count": len(sentences),
            "mean_words_per_sentence": (
                round(len(words) / len(sentences), 2) if sentences else None),
            "type_token_ratio": (
                round(len({w.lower() for w in words}) / len(words), 4)
                if words else None),
        })
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    parser.add_argument("-o", "--out", default="crucible-out")
    parser.add_argument("--root")
    args = parser.parse_args()

    repo, root = find_repo_and_root(args.target)
    if args.root:
        root = (repo / args.root).resolve()
    doc = flatten(root, repo)
    macros = collect_macros(doc)
    ing = load_json(Path(args.out) / "facts" / "ingest.json")

    rendered_lines = []
    comments = []
    revision_commands = []
    for line in doc.lines:
        if line.in_verbatim:
            continue
        plain = to_prose(demacro(line.code, macros))
        if plain:
            rendered_lines.append((line, plain))
        if line.comment.strip("% "):
            comments.append({"file": line.file, "line": line.lineno,
                             "text": line.comment.strip()[:240]})
        if REVISION_COMMAND_RX.search(line.code):
            revision_commands.append({"file": line.file, "line": line.lineno,
                                      "text": line.code.strip()[:240]})

    full_prose = "\n".join(text for _, text in rendered_lines)
    titled_sections = [
        {"title": block.get("section"), "file": block.get("file"),
         "line": block.get("line"), "prose": block.get("prose", "")[:4000]}
        for block in ing.get("prose_by_section", [])
        if DISCLOSURE_TITLE_RX.search(block.get("section", ""))
    ]

    direct = []
    for line, plain in rendered_lines:
        if WRITING_USE_RX.search(plain) or FULL_GENERATION_RX.search(plain):
            direct.append({
                "file": line.file, "line": line.lineno,
                "excerpt": plain[:500],
                "full_generation_language": bool(FULL_GENERATION_RX.search(plain)),
                "tools_mentioned": sorted(set(
                    m.group(0) for m in AI_TOOL_RX.finditer(plain))),
            })
    # Disclosure sentences frequently wrap across TeX source lines.  Scan the
    # complete disclosure section as well as individual lines so a line break
    # cannot hide an explicit writing-use statement.
    for section in titled_sections:
        prose = section["prose"]
        disclosed_writing = (
            WRITING_USE_RX.search(prose) or FULL_GENERATION_RX.search(prose) or
            (AI_TOOL_RX.search(prose) and WRITING_ACTIVITY_RX.search(prose))
        )
        if not disclosed_writing:
            continue
        if any(item["file"] == section["file"] and
               item["line"] >= section["line"] for item in direct):
            continue
        direct.append({
            "file": section["file"], "line": section["line"],
            "excerpt": prose[:1000],
            "full_generation_language": bool(FULL_GENERATION_RX.search(prose)),
            "tools_mentioned": sorted(set(
                m.group(0) for m in AI_TOOL_RX.finditer(prose))),
            "section_level": True,
        })

    leaks = []
    for kind, pattern in GENERATION_LEAKS.items():
        for line, plain in rendered_lines:
            if pattern.search(plain):
                leaks.append({"kind": kind, "file": line.file,
                              "line": line.lineno, "excerpt": plain[:500]})

    out = {
        "source_scope": "tex-source",
        "direct_disclosures": direct,
        "disclosure_sections": titled_sections,
        "generation_artifacts": leaks,
        "revision_traces": {
            "source_comment_count": len(comments),
            "source_comment_examples": comments[:30],
            "revision_command_count": len(revision_commands),
            "revision_command_examples": revision_commands[:30],
            "multiple_root_files": ing.get("multiple_roots", False),
        },
        "version_control": git_provenance(repo),
        "section_style": section_stats(ing),
        "ai_term_contexts": snippets(AI_TOOL_RX, full_prose),
        "limitations": [
            "Writing style and stylometry are not reliable AI detectors.",
            "Absence of a disclosure or generation artifact is not evidence "
            "that AI was not used.",
            "Repository history records edits, not the origin of prose pasted "
            "into those edits.",
            "A fully-AI label requires direct provenance or multiple "
            "independent high-specificity signals; fluency alone is never enough.",
        ],
    }
    write_json(Path(args.out) / "facts" / "authorship.json", out)
    print("authorship: "
          f"{len(direct)} direct disclosure(s), "
          f"{len(titled_sections)} disclosure section(s), "
          f"{len(leaks)} generation artifact(s), "
          f"git_history={out['version_control']['available']}")


if __name__ == "__main__":
    main()
