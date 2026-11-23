#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Aethercloud LLC
#
# gr58-check.sh — Stop hook. Scans the agent's final text for the turn with
# ~/.claude/tools/gr58_scan.py and, when it holds a first-person word, returns
# {"decision":"block","reason":...} so the agent sends a corrected message
# (GR-58 (c)) with those words removed. GR-58 (b) candidates are not reported.
# Full reference: gr58-check.md.
#
# Fail-open: a missing interpreter or scan script, or any error, ends with no
# output and exit 0, so the hook can never stop a session from ending.
scan="$HOME/.claude/tools/gr58_scan.py"
command -v python3 >/dev/null 2>&1 && [ -f "$scan" ] || exit 0
exec python3 "$scan" --hook
