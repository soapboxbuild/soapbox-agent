# Soapbox Agent

The core intelligence layer built into every Soapbox portfolio. Skills in this repo are automatically available to every asset's AI — they cannot be removed by users.

## Skills

- **white-hat-review** — Skeptically audits agent-generated reports: verifies numbers against source documents, flags unsupported claims, checks methodology versions, and suggests corrections before outputs reach clients or inform decisions.

## Adding Skills

Skills added to `skills/` are automatically picked up by the platform. Each skill is a directory containing `SKILL.md` following the [agentskills.io](https://agentskills.io/specification) spec.
