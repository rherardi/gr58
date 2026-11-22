#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Aethercloud LLC
"""GR-58 candidate scan: lists words that may attribute a mind to code, and first-person words.

GR-58 is the rule described in gr58-check.md: an AI agent's own text attributes no
psychological state, mental act or consciousness to code that produces output, and
uses no first-person word that refers to the agent. The scan finds candidates only;
each hit is then read and classified (subject or owner, implied actor, programming
sense, quoted material). Text the scan skips: fenced code, inline code, double-quoted
spans (including the agent's own quoted drafts), cross-references such as "see R6",
Appendix I style references, and the text of a GR-58 rule definition itself.

  python3 ~/.claude/tools/gr58_scan.py FILE ...      one line per hit: file:line, word, context
  python3 ~/.claude/tools/gr58_scan.py --self-test   runs the built-in controls; exit 1 on failure
  python3 ~/.claude/tools/gr58_scan.py --hook        Stop-hook mode, called by ~/.claude/hooks/gr58-check.sh
"""
import json
import re
import sys

# ---------------------------------------------------------------------------
# Word lists: what counts as a candidate
# ---------------------------------------------------------------------------

# (b) mind words with inflected and nominal forms; a hyphen may border a match ("self-aware").
B_FORMS = [
    r"judge?ments?", r"decid(?:e|es|ed|ing)", r"decisions?",
    r"(?:choose|chooses|chose|chosen|choosing|choices?)",
    r"(?:think|thinks|thinking|thought)", r"beliefs?", r"believ(?:e|es|ed|ing)",
    r"(?:understand|understands|understanding|understood)",
    r"(?:know|knows|knew|known|knowing)", r"(?:feel|feels|felt|feeling)",
    r"want(?:s|ed|ing)?", r"wish(?:es|ed|ing)?", r"(?:try|tries|tried|trying)",
    r"assum(?:e|es|ed|ing)", r"assumptions?", r"notic(?:e|es|ed|ing)",
    r"realiz(?:e|es|ed|ing)", r"intend(?:s|ed|ing)?", r"intentions?",
    r"prefer(?:s|red|ring)?", r"preferences?", r"conclud(?:e|es|ed|ing)",
    r"conclusions?", r"approv(?:e|es|ed|ing)", r"approvals?",
    r"obey(?:s|ed|ing)?", r"aware", r"confident",
    r"(?:see|sees|saw|seen|seeing)",
]
B_RE = re.compile(r"(?<!\w)(" + "|".join(B_FORMS) + r")(?!\w)", re.I)

# (c) first-person words, matched with case so "US" and the index variable "i" are not hits; "let's" is "let us".
C_RE = re.compile(
    r"(?<![\w-])(I|[Mm]e|ME|[Mm]y|MY|[Mm]ine|[Mm]yself|[Ww]e|WE|[Uu]s|[Oo]ur|OUR|[Oo]urs"
    r"|[Ll]et['’]s)(?![\w-])"
)

# ---------------------------------------------------------------------------
# Skip patterns: text outside the rule
# ---------------------------------------------------------------------------

FENCE_RE = re.compile(r"```.*?```", re.S)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
# A quoted span may run across line breaks but not across a blank line (a paragraph end).
QUOTE_RE = re.compile(r'"(?:[^"\n]|\n(?![ \t]*\n))*"|“(?:[^”\n]|\n(?![ \t]*\n))*”')
XREF_RE = re.compile(
    r"\b[Ss]ee\s+(?:below|above|also|the next|[RDQCP]-?\d|section|§|Appendix|Verification|Purpose"
    r"|[A-Z][\w.-]*\.md|\*|\[|\()"
)
ROMAN_I_RE = re.compile(r"Appendix[ \t]+I\b|\bI\.\d|\bI/O\b|\(I\)|\|[ \t]*I[ \t]*\||(?:^|[ \t])I(?=[ \t]+key\b)", re.M)
# A GR-58 rule definition: "GR-58 [KIND] TITLE" in a plain-text rule file, "## GR-58 [KIND] TITLE" in Markdown.
GR58_START_RE = re.compile(r"^(?:## )?GR-58 \[")

# ---------------------------------------------------------------------------
# Text cleaning: blank skipped spans, keeping line numbers
# ---------------------------------------------------------------------------


def blank(match):
    """Replace a skipped span with spaces, keeping its newlines so line numbers stay true."""
    return re.sub(r"[^\n]", " ", match.group(0))


def skip_gr58(text):
    """Blank the text of a GR-58 rule definition, which is the rule's own definition and outside the scan.

    The block starts at a GR-58 header line. In a plain-text rule file ("GR-58 [") it ends at the
    first blank line, since that format keeps a rule's fields on contiguous lines; in Markdown
    ("## GR-58 [") it ends at the next heading. Runs after fenced code is blanked, so a header
    inside code starts no block.
    """
    lines, mode = text.split("\n"), None
    for i, line in enumerate(lines):
        if mode is None and GR58_START_RE.match(line):
            mode = "markdown" if line.startswith("## ") else "plain"
        elif mode == "plain" and not line.strip():
            mode = None
        elif mode == "markdown" and line.startswith("#"):
            mode = None
        if mode:
            lines[i] = ""
    return "\n".join(lines)


def clean(text):
    """Remove every span the scan skips, keeping line numbers; called once per file before matching."""
    text = skip_gr58(FENCE_RE.sub(blank, text))
    for pattern in (INLINE_CODE_RE, QUOTE_RE, XREF_RE, ROMAN_I_RE):
        text = pattern.sub(blank, text)
    return text

# ---------------------------------------------------------------------------
# Scanning: list candidates line by line
# ---------------------------------------------------------------------------


def scan(text):
    """Yield (line number, word, context) for each candidate in the cleaned text; the core of every run."""
    for number, line in enumerate(clean(text).split("\n"), 1):
        hits = [(m.start(), m.end(), m.group(1)) for m in B_RE.finditer(line)]
        hits += [(m.start(), m.end(), m.group(1)) for m in C_RE.finditer(line)]
        for start, end, word in sorted(hits):
            yield number, word, line[max(0, start - 70):end + 45].strip()

# ---------------------------------------------------------------------------
# Built-in controls: planted violations and a clean specimen
# ---------------------------------------------------------------------------


NEGATIVE = """The scan decided the hit was content.
I ran the suite.
We ran the suite.
Let's run the suite.
Trace callers before concluding.
The check is self-aware.
The tool is confident the value is correct.
The cache layer decides whether a stored entry is stale.
This plan's assumptions: the unit is the byte.
see
R6 is cited, and the agent assumes the scope.
```
GR-58 [OPERATIONAL] quoted inside code in a message.
```
The agent believes the header above changes nothing.
GR-58 [OPERATIONAL] A PLAIN-TEXT HEADER.
TRIGGER: before deciding.

The check thinks the plain-text block has ended.
## GR-58 [OPERATIONAL] A MARKDOWN HEADER.

**TRIGGER:** a choice made.

## GR-59 [OPERATIONAL] THE NEXT RULE.
The scan wants the Markdown block to have ended."""

CLEAN = """Appendix I lists the lifecycle documents.
See Appendix I.8 and section 2.1 for the US English rule; see R6 and see below.
Use `try:` and `for i in range(n)` in the probe; the loop index i starts at 0.
The quoted instruction reads "We decide the format" and the gate determines the result.
```
the agent decides
```
GR-58 [OPERATIONAL] A REFERENCE TO CODE PRODUCING OUTPUT ATTRIBUTES NO MIND.
TRIGGER: writing a sentence; for example a choice made, before deciding.

## GR-58 [OPERATIONAL] THE SAME RULE IN MARKDOWN.

**TRIGGER:** a choice made, before deciding.

## GR-59 [OPERATIONAL] THE NEXT RULE.
The user's request reads "OK, let's use
the shorter form," quoted across a line break.
The SDK I/O path and the region us-east-1 are unaffected."""


def self_test():
    """Run the built-in controls: every NEGATIVE line is a hit, CLEAN yields none; exit status reports it."""
    negative_lines = {n for n, _, _ in scan(NEGATIVE)}
    expected = set(range(1, NEGATIVE.count("\n") + 2)) - {10, 12, 13, 14, 16, 17, 18, 20, 21, 22, 23, 24}
    missed = sorted(expected - negative_lines)
    clean_hits = list(scan(CLEAN))
    line_10 = [w for n, w, _ in scan(NEGATIVE) if n == 10]
    line_11 = [w for n, w, _ in scan(NEGATIVE) if n == 11]
    print(f"negative control: {len(expected) - len(missed)} of {len(expected)} lines caught; missed {missed}")
    print(f"cross-reference split by a line break skipped: {'yes' if not line_10 else 'no'}")
    print(f"line numbers kept across a skipped cross-reference: {'yes' if line_11 == ['assumes'] else 'no'}")
    print(f"clean control: {len(clean_hits)} hits {clean_hits}")
    return 0 if not missed and not clean_hits and not line_10 and line_11 == ["assumes"] else 1

# ---------------------------------------------------------------------------
# Stop-hook mode: read the turn from the transcript, return a decision
# ---------------------------------------------------------------------------


FIRST_PERSON = {"i", "me", "my", "mine", "myself", "we", "us", "our", "ours", "let's", "let’s"}
REASON_LIMIT = 1800   # Claude Code truncates hook context beyond about 2 KB


def last_turn_text(transcript_path):
    """Return the agent's visible text since the last user-typed entry in a session transcript (JSONL).

    Tool results arrive as user entries too; only an entry carrying the user's own text
    (a string, or a text block) starts a new turn.
    """
    entries = []
    with open(transcript_path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                entries.append(json.loads(line))
            except ValueError:
                continue
    texts = []
    for entry in entries:
        message = entry.get("message") or {}
        content = message.get("content")
        if entry.get("type") == "user" and message.get("role") == "user":
            typed = isinstance(content, str) or any(
                isinstance(b, dict) and b.get("type") == "text" for b in content or [])
            if typed:
                texts = []
        elif entry.get("type") == "assistant" and isinstance(content, list):
            texts += [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
    return "\n\n".join(t for t in texts if t.strip())


def hook_decision(event):
    """Map one Stop-hook input to a decision: block on a first-person hit, else no output.

    Returns the JSON string to print, or "" for no output. A block lists the first-person
    hits and any (b) candidates; stop_hook_active ends the cycle after one correction turn.
    """
    if event.get("stop_hook_active"):
        return ""
    text = last_turn_text(event["transcript_path"])
    hits = list(scan(text))
    first = [h for h in hits if h[1].lower() in FIRST_PERSON]
    if not first:
        return ""
    others = [h for h in hits if h[1].lower() not in FIRST_PERSON]
    lines = ["GR-58 (c): the last message contains first-person words. Where the referent is the agent,"
             " send a corrected message; where it is a person or quoted material, say so in one line."]
    lines += [f"  line {n}: {w!r}: {c}" for n, w, c in first]
    if others:
        lines.append("GR-58 (b) candidates to classify in the same pass:")
        lines += [f"  line {n}: {w!r}: {c}" for n, w, c in others]
    reason = "\n".join(lines)
    if len(reason) > REASON_LIMIT:
        reason = reason[:REASON_LIMIT].rsplit("\n", 1)[0] + "\n  (list truncated)"
    return json.dumps({"decision": "block", "reason": reason})


def hook_main():
    """Stop-hook entry: read the event from stdin and print the decision; fails open on any error."""
    try:
        output = hook_decision(json.load(sys.stdin))
    except Exception:   # a broken hook must never wedge a session
        return 0
    if output:
        print(output)
    return 0

# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def main(argv):
    """Entry point: --self-test runs the controls, --hook runs Stop-hook mode, otherwise each named file is scanned."""
    if argv == ["--self-test"]:
        return self_test()
    if argv == ["--hook"]:
        return hook_main()
    for path in argv:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for number, word, context in scan(handle.read()):
                print(f"{path}:{number}\t{word}\t{context}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
