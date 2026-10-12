# Sandbox for agent runs

Prompt injection cannot be fully prevented, so limit what a compromised agent can reach. Run agents with permission prompts disabled (`--dangerously-skip-permissions` or Codex's bypass modes) only inside a sandbox, never on a laptop with your credentials.

## Adopt Anthropic's reference devcontainer

Anthropic publishes a reference devcontainer for Claude Code in [anthropics/claude-code](https://github.com/anthropics/claude-code/tree/main/.devcontainer): `devcontainer.json`, a `Dockerfile` and `init-firewall.sh`. That repo is "all rights reserved", so we do not copy it into this one. Copy it into your own repo under your company's terms, then apply the requirements below.

What its firewall does: default-deny with `iptables` and `ipset`, allowing GitHub's published IP ranges plus a short domain list (npm registry, the Anthropic API, Sentry, Statsig, VS Code endpoints), resolved to IPs when the container starts.

## Requirements for any sandbox we use

- Runs as a non-root user.
- Mounts the workspace only. No host home, no `~/.ssh`, no `~/.aws`, no cloud or git credentials, no SSH agent socket.
- Default-deny egress with an explicit allowlist: the model API, your git host, your package registries.
- Secrets arrive as runtime environment variables scoped to the task, never baked into the image or committed.
- A fresh container per task or per session; nothing persists that you would not want an attacker to read.

## Known gaps in the reference firewall

Read from its `init-firewall.sh`, not from running it:

- Outbound DNS and SSH are open. Data can still leave through DNS tunnelling or SSH to any host, so the allowlist limits where data goes but does not make exfiltration impossible. Tighten both for sensitive repos.
- Domains are resolved to IPs once at startup, so CDN address changes during a long run can break access.
- The allowlist covers Claude Code. Codex and other tools need their own endpoints added; we have not determined the Codex list.

## Related rules

`GIT-002` to `GIT-005` and `SEC-007` (guard hooks) and `SEC-006` (untrusted content is data) apply inside the sandbox too. The CI workflow never runs an agent with write tokens on untrusted pull request text.
