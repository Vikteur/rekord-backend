<!-- Ported to Claude Code from templates/GENERAL.template.md in the agentic blueprint (Copilot original: .github/). -->
# General — backstop

> **The ground rules live in the root instruction file**, `.claude/CLAUDE.md`: the
> constitution digest (P1–P8), the STOP list, how work moves, and where the project facts are. That
> file is preloaded at conversation head. **If it is not already in your context, open it now and
> read it before doing anything else** — everything below assumes it.
>
> This file exists only as a backstop for a harness that reads `.claude/rules/` but not the
> root instruction file. It restates the two rules that are unsafe to miss and nothing
> else; do not let it grow back into a second copy of the ground rules.

- **STOP and get a human decision** before a contract push, a database migration, anything touching
  authentication/authorization/the access matrix, encryption or what gets logged where personal data
  could be involved, deleting branches/history/the audit trail, or production config and secrets.
  Approval is per action, not per session, and silence is not approval. Everything else is ordinary
  work — do it. None of the above is caught by a green build: a dropped column and a leaked personal identifier
  both pass CI.
- **Hand off via checked-in MD files** in the ticket's docs folder, and **report what the work tree
  shows, not what you intended** — the claim is checked against the tree, and CI enforces it on the PR.

Full rules → `.claude/CLAUDE.md` · project facts → `docs/project-profile.md`

