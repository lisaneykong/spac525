#!/usr/bin/env python3
"""Check a SPAC 525 draft against the 525 rule (Lisaney Kong style rules).

Usage:
    python check_draft.py draft.txt [--skip-last N] [--min 0] [--max 149]
                                    [--max-semicolons 1] [--max-colons 1]

Paragraphs are separated by blank lines. Short lines without ending
punctuation (titles, headings) are treated as headings and skipped.
Checking stops at a "References" heading, so a full draft can be passed.
--skip-last N also excludes the final N paragraphs.
Exit code 0 when clean, 1 when anything is flagged.
"""
import argparse
import re
import sys

BANNED = [
    "delve", "elevate", "foster", "unlock", "landscape", "underscore",
    "pivotal", "testament", "beacon", "tapestry", "realm", "garner", "vital",
]

AI_WORDS = [
    "intricate", "crucial", "showcase", "enhance", "vibrant", "boast",
    "align with", "seamless", "robust", "multifaceted", "ever-evolving",
    "holistic", "additionally", "moreover", "furthermore", "groundbreaking",
    "cutting-edge", "game-changer", "navigate the", "navigating the",
    "leverage", "sharpens", "breathtaking",
]

AI_PHRASES = [
    r"it is (important|worth|crucial|essential) to (note|mention|remember|consider)",
    r"worth noting", r"worth mentioning", r"in conclusion", r"in summary",
    r"\boverall,", r"\bin short,", r"\bin addition\b", r"on the other hand",
    r"plays? an? (key|vital|significant|crucial|important|pivotal) role",
    r"stands? as an?", r"serves? as an?", r"lasting (impact|legacy)",
    r"enduring legacy", r"key turning point", r"watershed moment",
    r"deeply rooted", r"rich (cultural )?(heritage|history|tapestry)",
    r"broader (movement|context|landscape)",
    r"\bnot (just|only|merely) [^.;]{1,60}[,;] (but|it is|it's)",
    r"some (critics|experts|observers|scholars|analysts) (argue|say|suggest|note)",
    r"experts (say|agree|suggest)", r"industry reports", r"observers note",
    r"no discussion (of [^.]+ )?would be complete",
    r"in this (article|post|essay)\b",
    r", (highlighting|underscoring|emphasizing|reflecting|ensuring|showcasing|demonstrating) ",
    r"from [a-z ]{3,30} to [a-z ]{3,30}, ",
    r"challenges and future (outlook|directions)",
    r"great (point|post|question)!?", r"i really enjoyed",
    r"i hope this helps", r"\bcertainly!",
    r"as of my (last|knowledge)", r"knowledge cutoff",
]

# Labeled or memo-style BLUF openers, anywhere in a paragraph.
LABELED_BLUF = re.compile(
    r"(^|[.!?]\s+)(bottom line\b|bluf\b|the key takeaway|key takeaway|simply put,|tl;?dr)",
    re.IGNORECASE,
)
# Weak opinion openers at the start of a paragraph.
WEAK_OPENER = re.compile(r"^(i believe|i think|i feel|in my opinion)\b", re.IGNORECASE)
IN_MY_OPINION = re.compile(r"\bin my opinion\b", re.IGNORECASE)
# Page or paragraph numbers inside a parenthetical citation.
PAGE_CITE = re.compile(r"\([^()]*\b(p|pp|para|paras)\.\s*\d[^()]*\)", re.IGNORECASE)

APOS = "['’]"
CONTRACTION = re.compile(
    r"\b\w+" + APOS + r"(t|re|ve|ll|d|m)\b|\b(it|that|there|here|what|who|he|she|let)" + APOS + r"s\b",
    re.IGNORECASE,
)
POSSESSIVE = re.compile(r"\b\w+" + APOS + r"s\b|\b\w+s" + APOS + r"(?=\s)", re.IGNORECASE)
EM_DASH = re.compile("—|–| -- |(?<=\\w)--(?=\\w)")
REFERENCES_HEADING = re.compile(r"^#*\s*(references|reference list|works cited)\s*$", re.IGNORECASE)


def is_heading(par: str) -> bool:
    words = par.split()
    return par.lstrip().startswith("#") or (len(words) < 15 and not par.rstrip().endswith((".", "?", "!", ":", ";")))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--skip-last", type=int, default=0)
    ap.add_argument("--min", type=int, default=0)
    ap.add_argument("--max", type=int, default=149)
    ap.add_argument("--max-semicolons", type=int, default=1)
    ap.add_argument("--max-colons", type=int, default=1)
    args = ap.parse_args()

    text = open(args.file, encoding="utf-8").read()
    pars = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    for i, par in enumerate(pars):
        if REFERENCES_HEADING.match(par):
            pars = pars[:i]
            break
    if args.skip_last:
        pars = pars[: -args.skip_last] if args.skip_last < len(pars) else []

    problems = 0
    n = 0
    for par in pars:
        if is_heading(par):
            continue
        n += 1
        flat = " ".join(par.split())
        low = flat.lower()
        wc = len(flat.split())
        issues = []
        if not (args.min <= wc <= args.max):
            issues.append(f"length {wc} words (cap is {args.max})")
        if WEAK_OPENER.search(flat):
            issues.append("weak opinion opener (never open with I believe / I think / I feel / In my opinion)")
        elif IN_MY_OPINION.search(flat):
            issues.append("weak opinion phrase: in my opinion")
        bluf = LABELED_BLUF.search(flat)
        if bluf:
            issues.append("labeled BLUF: " + bluf.group(2))
        contractions = {m.group(0) for m in CONTRACTION.finditer(flat)}
        if contractions:
            issues.append("contractions: " + ", ".join(sorted(contractions)))
        poss = {m.group(0) for m in POSSESSIVE.finditer(flat)} - contractions
        if poss:
            issues.append("possessive apostrophes: " + ", ".join(sorted(poss)))
        if EM_DASH.search(flat):
            issues.append("em/en dash or double hyphen")
        banned = [w for w in BANNED if re.search(r"\b" + w + r"\w*", low)]
        if banned:
            issues.append("banned words: " + ", ".join(banned))
        aiw = [w for w in AI_WORDS if re.search(r"\b" + re.escape(w) + r"\w*", low)]
        if aiw:
            issues.append("AI-flavored words: " + ", ".join(aiw))
        hits = [m.group(0) for p in AI_PHRASES for m in [re.search(p, low)] if m]
        if hits:
            issues.append("AI patterns: " + " | ".join(h.strip() for h in hits))
        pages = [m.group(0) for m in PAGE_CITE.finditer(flat)]
        if pages:
            issues.append("page/paragraph number in citation: " + " | ".join(pages))
        if flat.count(";") > args.max_semicolons:
            issues.append(f"{flat.count(';')} semicolons (max {args.max_semicolons})")
        if flat.count(":") > args.max_colons:
            issues.append(f"{flat.count(':')} colons (max {args.max_colons})")

        status = "OK" if not issues else "FIX"
        print(f"Paragraph {n} [{wc} words] {status}: {flat[:70]}...")
        for i in issues:
            print(f"    - {i}")
        problems += bool(issues)

    print(f"\n{n} paragraphs checked, {problems} need fixes.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
