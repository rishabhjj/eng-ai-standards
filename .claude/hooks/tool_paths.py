"""Print the file paths a tool call touches, one per line. Reads the hook JSON from stdin.

Claude Code sends tool_input.file_path. Codex sends file edits as apply_patch with the patch
text in tool_input.command, so paths come from its "*** Add|Update|Delete File:" headers.
With --resolve, symlink destinations are printed too.
"""
import json
import os
import re
import sys

try:
    tool_input = json.load(sys.stdin).get("tool_input", {})
except (ValueError, AttributeError):
    sys.exit(0)

paths = []
if tool_input.get("file_path"):
    paths.append(tool_input["file_path"])
command = tool_input.get("command")
if isinstance(command, str):
    paths += re.findall(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", command, re.M)
    paths += re.findall(r"^\*\*\* Move to: (.+)$", command, re.M)
paths = [p.strip() for p in paths]
if "--resolve" in sys.argv:
    # also print where each path really lands, so a symlink (file or parent dir) cannot hide a target
    paths += [os.path.realpath(p) for p in paths if os.path.realpath(p) != os.path.abspath(p)]
print("\n".join(paths))
