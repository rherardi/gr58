# GR-58

GR-58 is a rule for AI agents, with a Claude Code `Stop` hook that checks it. The rule keeps an agent's own text from attributing a psychological state, a mental act or consciousness to software that produces output by algorithm, and from using first-person words that refer to code.

## Contents

| File | Installed location | What it is |
|---|---|---|
| `README.md` | stays in the repository | Purpose, mechanisms, limitations, installation and configuration. |
| `LICENSE` | stays in the repository | The Apache License, Version 2.0. |
| `gr58_scan.py` | `~/.claude/tools/` | Lists GR-58 candidates in text. Runs on files, runs its own controls, or runs as a `Stop` hook. |
| `gr58-check.sh` | `~/.claude/hooks/` | The `Stop` hook wrapper that runs `gr58_scan.py --hook`. |
| `gr58-check.md` | `~/.claude/hooks/` | Reference for the hook: the rule, wiring, behavior and limits. |
| `install_hook.md` | `~/.claude/hooks/` | The `settings.json` entry that registers the hook, ready to paste or merge. |

## Purpose of GR-58

The rule applies to the agent's own text from the time it is adopted, not to existing artifacts or to text a person wrote. Its scope, requirements, allowed programming senses and an example are stated in the "Rule" section of `gr58-check.md`.

## Mechanisms

GR-58 is applied through three mechanisms.

1. **Rule text.** The "Rule" section of `gr58-check.md` goes into the agent's instructions, for example `~/.claude/CLAUDE.md`, so the agent reads it at the start of every session.
2. **Candidate scan.** `gr58_scan.py` lists words that may break the rule. Its output is a list of candidates, not a compliance result; each hit is read and classified.
   - **Matched:** the rule's example words with their inflected and noun forms (decides, decision, choice, assumption), including hyphenated forms such as "self-aware". First-person words are matched with case, so "US" and the index variable `i` are not hits.
   - **Skipped:** fenced and inline code, double-quoted spans (straight and curly, including across a line break within a paragraph), cross-references such as "see R6" or "see below", Appendix I style references, and the text of a GR-58 rule definition.
   - **Output:** one line per hit: `file:line`, the word, and its context.
3. **Stop hook.** At the end of each Claude Code turn, `~/.claude/hooks/gr58-check.sh` runs `gr58_scan.py --hook`:
   - It reads the turn's text from the session transcript.
   - When the text holds a first-person word, it returns a block. The agent then sends a correction, or states that the referent is a person or quoted material. The feedback also lists any other GR-58 candidates for the agent to classify.
   - A turn with no first-person hit ends normally.
   - The correction turn the hook causes is not blocked again.
   - Any error produces no output, so the hook never keeps a session from ending.

## Install and configure for Claude Code

Requirements: `bash`, `python3`, and `jq` for the merge command in step 4. Run the commands from a clone of this repository.

1. **Place the files.**

   ```bash
   mkdir -p ~/.claude/tools ~/.claude/hooks
   cp gr58_scan.py ~/.claude/tools/
   cp gr58-check.sh gr58-check.md install_hook.md ~/.claude/hooks/
   ```

2. **Add the rule to the agent's instructions.** Copy the "Rule" section of `gr58-check.md` into `~/.claude/CLAUDE.md`.

3. **Check the scan.** The command prints the control results and exits with status 0 when they pass:

   ```bash
   python3 ~/.claude/tools/gr58_scan.py --self-test
   ```

4. **Register the hook.** `~/.claude/hooks/install_hook.md` holds the entry for `~/.claude/settings.json`.
   - **If `~/.claude/settings.json` does not exist,** copy `~/.claude/hooks/install_hook.md` to it.
   - **If it exists and has no `Stop` entry under `hooks`,** merge the entry:

     ```bash
     cp ~/.claude/settings.json ~/.claude/settings.json.bak
     jq -s '.[0] * .[1]' ~/.claude/settings.json.bak ~/.claude/hooks/install_hook.md > ~/.claude/settings.json
     ```

   - **If `hooks` already has a `Stop` entry,** add the inner object, the one with `"hooks"`, to that `Stop` array by hand. The `jq` merge above would replace the existing array.

5. **Activate.** Start a new session, or review the change in `/hooks`, so Claude Code reads the new setting.

6. **Test the hook.** These commands write a one-line transcript containing a first-person word and run the hook on it. The expected output is a JSON object whose `decision` is `block`:

   ```bash
   t=$(mktemp)
   printf '%s\n' '{"type":"user","message":{"role":"user","content":"go"}}' \
     '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"I ran the suite."}]}}' > "$t"
   printf '{"transcript_path":"%s","stop_hook_active":false}' "$t" | bash ~/.claude/hooks/gr58-check.sh
   rm -f "$t"
   ```

   With `"stop_hook_active":true`, or with the text changed to `The suite ran.`, the hook prints nothing.

### Run the scan by hand

```bash
python3 ~/.claude/tools/gr58_scan.py FILE ...
```

### Uninstall

Remove the `Stop` entry that runs `gr58-check.sh` from `~/.claude/settings.json`, delete `~/.claude/tools/gr58_scan.py`, `~/.claude/hooks/gr58-check.sh`, `~/.claude/hooks/gr58-check.md` and `~/.claude/hooks/install_hook.md`, then start a new session.

## Limitations

### What the hook enforces

- **The hook runs after the message is shown.** It causes a correction turn; it cannot withhold a message.
- **Only first-person words block.** Another GR-58 candidate, such as "the gate decides", appears only in the feedback for a turn that also has a first-person hit; on its own it passes.
- **One correction turn per block.** The correction turn runs with `stop_hook_active` set and is not checked again, so a correction that still breaks the rule passes.
- **Feedback is capped** at about 1,800 characters; a longer hit list ends with "(list truncated)".

### What the scan covers

- **Only the agent's messages are scanned.** Text the agent writes into files (plans, reports, memory entries) is not.
- **The scan lists candidates, not violations.** Whether a first-person word refers to the agent, and whether a word attributes a mind to code, is settled by reading.
- **The word list samples the rule.** A mind-word construction not on the list is not found.
- **Skipped text is not checked.** Quoted spans are skipped, including the agent's own drafts put in quotes. In a plain-text rule file, text directly after a GR-58 header is skipped up to the next blank line.

### Where it runs

- **Only Claude Code is covered.** The hook uses the Claude Code `Stop` hook interface.
- **The hook runs in every project** in which Claude Code loads `~/.claude/settings.json`.
- **Hook settings may be read only when a session starts.** The Claude Code hook documentation says so, although in testing a running session ran a newly added `Stop` entry without a restart. If the hook does not fire, restart the session or review the change in `/hooks`.
- **A higher-level setting can switch it off.** A `disableAllHooks` setting in project settings or an organization-wide settings policy stops it from running.
- **It fails open.** With `bash`, `python3` or `gr58_scan.py` missing, or on any error, the hook produces no output, and nothing reports that it did not run.

## License

Licensed under the Apache License, Version 2.0 (SPDX-License-Identifier: Apache-2.0); see `LICENSE`. Each source file carries the SPDX identifier and the copyright line.

## Maintainers

Maintained by Aethercloud LLC.

Questions, issues and contributions: maintainers_list@aethercloud.net
