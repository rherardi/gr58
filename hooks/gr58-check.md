# gr58-check.sh

Reference for the Claude Code `Stop` hook that checks an AI agent's final text in each turn against GR-58, the rule on references to code that produces output.

## Rule

GR-58 keeps an AI agent's own text from attributing a psychological state, a mental act or consciousness to software that produces output by algorithm. It applies to text the agent writes: messages, plans, reports, memory entries and its own configuration.

A sentence is in scope when:

- its subject or owner is code that produces output: the AI agent, a tool, scan, check, script, gate, test run, program, service, module or function; or
- it is a passive, nominal, imperative or non-finite construction in the agent's own text whose implied actor is the agent ("a choice made", "before deciding").

In scope, the sentence:

- names the code and gives it a program verb, such as reads, writes, runs, searches, compares, matches, detects, reports or determines;
- uses no word whose meaning there requires a mind, such as decide, choose, think, know, assume, intend, prefer or conclude, and no denial of such a capacity ("cannot know");
- uses no first-person word whose referent is the agent.

Ordinary programming senses are allowed:

- accept, reject and refuse, for code that performs a check;
- agree and comply, meaning consistent or conforming;
- see, meaning detect, access or read.

Quoted material, existing identifiers, and terms that the project's own rule files, its specification, or a standard it cites define keep their own wording.

Example: "the gate that decides whether the change was safe" is written "the gate that determines whether the change was safe."

To have the agent apply the rule, include its text in the agent's instructions, for example in `~/.claude/CLAUDE.md`.

## Wiring

| Location | Role |
|---|---|
| `~/.claude/settings.json`, `hooks.Stop` | Registers `bash "$HOME/.claude/hooks/gr58-check.sh"` |
| `~/.claude/hooks/gr58-check.sh` | Wrapper; fails open, then runs the scan in hook mode |
| `~/.claude/tools/gr58_scan.py --hook` | Reads the Stop event, extracts the turn's text, scans it, prints the decision |
| `~/.claude/tools/gr58_scan.py --self-test` | Built-in controls for the scan itself |

## Behavior

1. The event's `transcript_path` is read. The turn's text is every agent text block after the last entry carrying the user's own text; tool results do not start a turn. Claude Code can fire the `Stop` event before the final message is written to the transcript, so the event's `last_assistant_message` is appended when the transcript does not yet hold it. An event without that field makes the hook re-read the transcript for up to 3 seconds until the final message appears.
2. The scan skips fenced code, inline code, double-quoted spans, cross-references and Appendix I style references, then lists candidates.
3. A first-person hit (I, me, my, mine, myself, we, us, our, ours, let's) produces `{"decision":"block","reason":...}`. The reason lists those hits with line and context and directs the agent to resend the message with them removed. GR-58 (b) candidates are not reported.
4. A turn with no first-person hit produces no output and ends normally.
5. When `stop_hook_active` is true, the event comes from the correction turn the hook itself caused; the hook produces no output, so one block yields at most one extra turn.

## Limits

- The hook runs after the message is shown. It cannot withhold a message; it can only cause a correction.
- The scan lists candidates. Whether a first-person word refers to the agent, and whether a (b) word attributes a mind, is settled by reading.
- Quoted spans are skipped, including the agent's own quoted drafts.
- On any error the hook fails open with no output; the scan appends the traceback to `~/.claude/gr58/hook-errors.log`.
- Feedback is capped at about 1,800 characters and marked "(list truncated)" beyond that.
- The Claude Code hook documentation describes hook settings as captured when a session starts. In testing, a running session ran a newly added `Stop` entry without a restart; if the hook does not fire, restart the session or review the change in `/hooks`.

## License

SPDX-License-Identifier: Apache-2.0. Copyright 2026 Aethercloud LLC.
