"""Decide whether a shell command breaks GIT-002..005 or SEC-007. Reads the hook JSON on stdin.

Prints "RULE-ID: reason" and exits 2 to block; exits 0 otherwise. This is a safety net, not a
sandbox: it parses common git forms (global options, env config, chained and nested shells,
substitutions) but cannot see through gitconfig aliases, scripts or other binaries that call git.
CI and git hooks are the real gates.
"""
import json
import os
import re
import shlex
import sys
from pathlib import Path

SEPARATORS = {";", "&&", "||", "|", "&", "\n", "(", ")"}
# git global options that take a value as the next token
GLOBAL_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}
# commit short options that consume the rest of the cluster or the next token
COMMIT_VALUE_SHORT = set("mFcCtS")
SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
HOOK_KEYS = re.compile(r"core\.hookspath|commit\.gpgsign", re.I)
# env config that git reads: GIT_CONFIG_PARAMETERS='core.hooksPath=x', GIT_CONFIG_KEY_0=core.hooksPath
ENV_CONFIG = re.compile(r"^GIT_CONFIG_(?:PARAMETERS|KEY_\d+)=(.*)", re.S)
# group 1: the line up to and including the <<WORD marker; the body runs to a line holding only WORD
HEREDOC = re.compile(r"([^\n]*<<-?[ \t]*(['\"]?)(\w+)\2[^\n]*)\n.*?\n[ \t]*\3[ \t]*(?=[\n;&|>< #]|$)", re.S)
SUBST = re.compile(r"\$\(([^()]*)\)|`([^`]*)`")
FETCH = r"(?:curl|wget)\b"
SHELL = r"(?:\S*/)?(?:(?:ba|z|da|k)?sh|python[\d.]*|node|perl|ruby)\b"
REMOTE_CODE = [
    # curl … | [tee x |] [sudo -E] [env] [/bin/]bash|python3…  (`|` only, never `||`)
    re.compile(rf"{FETCH}[^|;&\n]*\|(?!\|)\s*(?:[^|;&\n]*\|(?!\|)\s*)*(?:sudo\s+(?:[^|;&\s]+\s+)*?)?(?:env\s+)?{SHELL}"),
    # eval "$(curl …)", bash -c "$(curl …)", bash <(curl …), source <(curl …)
    re.compile(rf"(?:\beval|{SHELL}\s+-[a-zA-Z]*c[a-zA-Z]*)\s+[\"']?(?:\$\(|`)\s*{FETCH}"),
    re.compile(rf"(?:{SHELL}|\bsource|(?<![\w./])\.)\s+(?:-\S+\s+)*<\(\s*{FETCH}"),
]


def tokens(command):
    try:
        lex = shlex.shlex(command, posix=True, punctuation_chars=";&|()\n")
        lex.whitespace_split = True
        lex.whitespace = " \t\r"
        return list(lex)
    except ValueError:
        return command.split()


def runs_as_code(prev):
    """True when the next token is executed: `eval ...` or `sh|bash|zsh -c ...` (also -lc, -ec)."""
    if prev and prev[-1] == "eval":
        return True
    return (len(prev) >= 2 and re.fullmatch(r"-[a-z]*c[a-z]*", prev[-1]) is not None
            and os.path.basename(prev[-2]) in SHELLS)


def segments(command, depth=0):
    """Yield simple commands as token lists, descending into quoted `sh -c "..."` bodies."""
    current = []
    for tok in tokens(command):
        if tok in SEPARATORS or set(tok) <= set(";&|()\n"):
            if current:
                yield current
            current = []
            continue
        if depth < 3 and any(c.isspace() for c in tok) and runs_as_code(current):
            yield from segments(tok, depth + 1)
        current.append(tok.lstrip("`$("))
    if current:
        yield current


def git_calls(seg):
    """For each `git` in a segment, yield (global option pairs, subcommand, args)."""
    for i, tok in enumerate(seg):
        if os.path.basename(tok) != "git":
            continue
        rest, glob = seg[i + 1:], []
        while rest and rest[0].startswith("-"):
            opt = rest.pop(0)
            if opt in GLOBAL_WITH_VALUE and rest:
                glob.append((opt, rest.pop(0)))
            else:
                glob.append(tuple(opt.split("=", 1)) if "=" in opt else (opt, ""))
        if rest:
            yield glob, rest[0], rest[1:]


def short_flags(args, stop=frozenset()):
    """Letters of clustered short options like -fd; a letter in `stop` ends the cluster."""
    out = set()
    for a in args:
        if a.startswith("-") and not a.startswith("--") and len(a) > 1:
            for ch in a[1:]:
                out.add(ch)
                if ch in stop:
                    break
    return out


def has_long(args, *names):
    """True for `--name` or an abbreviation git accepts (--har, --forc, --no-ver): 3+ letters after the dashes."""
    opts = [a.split("=", 1)[0] for a in args if a.startswith("--")]
    return any(o == n or (len(o) >= 5 and n.startswith(o)) for o in opts for n in names)


def whole_tree(args):
    """A pathspec that covers everything: ., ./., src/.., .., /, :/, *."""
    for a in args:
        if a.startswith("-") and a != "-":
            continue
        n = os.path.normpath(a)
        if a in {":/", ":/*", "*"} or n == "." or n.startswith("..") or (n.startswith("/") and not n.strip("/")):
            return True
    return False


def strip_data_heredocs(command):
    """Drop heredoc bodies that are data (cat, python...), keep those fed to a shell (bash <<EOF)."""
    def repl(m):
        head = tokens(m.group(1))
        return m.group(0) if any(os.path.basename(t) in SHELLS for t in head) else m.group(1) + "\n"
    return HEREDOC.sub(repl, command)


def git_violations(glob, sub, args):
    for opt, val in glob:
        key = val.split("=", 1)[0].lower()
        if opt in {"-c", "--config-env"} and HOOK_KEYS.search(key):
            yield "GIT-003", f"overriding {key} to skip hooks/signing"
        if opt in {"-c", "--config-env"} and key.startswith("alias."):
            yield "GIT-003", "a command-line alias can hide anything"
        if opt == "-c" and key == "clean.requireforce" and sub == "clean":
            yield "GIT-005", "git clean without --force guard"
    if has_long(args, "--no-verify", "--no-gpg-sign"):
        yield "GIT-003", "skipping git hooks/signing"
    if sub == "commit" and "n" in short_flags(args, COMMIT_VALUE_SHORT):
        yield "GIT-003", "commit -n skips git hooks"
    if sub == "push" and (has_long(args, "--force") or "f" in short_flags(args)
                          or any(a.startswith("+") for a in args)):
        yield "GIT-002", "force push"
    if sub == "reset" and has_long(args, "--hard"):
        yield "GIT-005", "git reset --hard"
    if sub == "clean" and (has_long(args, "--force") or "f" in short_flags(args)):
        yield "GIT-005", "git clean -f"
    if sub in {"checkout", "restore"} and whole_tree(args):
        yield "GIT-005", f"git {sub} of the whole tree discards local changes"
    if sub == "stash" and {"drop", "clear"} & set(args):
        yield "GIT-005", "git stash drop/clear loses stashed work"
    if sub == "add" and (has_long(args, "--all", "--update") or {"A", "u"} & short_flags(args) or whole_tree(args)):
        yield "GIT-004", "bulk staging; stage by pathspec"
    if sub == "commit" and (has_long(args, "--all") or "a" in short_flags(args, COMMIT_VALUE_SHORT)):
        yield "GIT-004", "commit -a stages everything; stage by pathspec"


def violations(command, depth=0):
    command = strip_data_heredocs(re.sub(r"\\\n", " ", command))
    if any(rx.search(command) for rx in REMOTE_CODE):
        yield "SEC-007", "pipe remote script to shell"
    if depth < 3:
        # $(...) and `...` run even inside double quotes
        for m in SUBST.finditer(command):
            yield from violations(m.group(1) or m.group(2), depth + 1)
    for seg in segments(command):
        for tok in seg:
            m = ENV_CONFIG.match(tok)
            if m and HOOK_KEYS.search(m.group(1)):
                yield "GIT-003", f"{tok.split('=', 1)[0]} overrides hooks/signing config"
        for glob, sub, args in git_calls(seg):
            yield from git_violations(glob, sub, args)


def disabled():
    """Non-security rule IDs the repo switched off in .eng-ai.json."""
    here = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    for d in (here, *here.parents):
        cfg = d / ".eng-ai.json"
        if cfg.is_file():
            try:
                return {r for r in json.loads(cfg.read_text()).get("disabled", []) if not r.startswith("SEC-")}
            except (ValueError, AttributeError, TypeError):
                return set()
    return set()


def main():
    try:
        command = json.load(sys.stdin).get("tool_input", {}).get("command", "")
    except (ValueError, AttributeError):
        return 0
    if isinstance(command, list):
        command = shlex.join(command)
    if not isinstance(command, str):
        return 0
    off = disabled()
    for rule, reason in violations(command):
        if rule not in off:
            print(f"{rule}: {reason}")
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
