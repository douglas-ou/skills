# Skills That Talk To Humans

Agent skills I use to align on requirements before a single line of code gets written.

## Why This Skill Exists

Too many technical questions. I'd rather the agent ask me in user scenarios — they're just easier to understand.

### Ask In User Scenarios

[`/by-usecase`](./skills/by-usecase/SKILL.md) runs the same thorough interview, but every question is phrased as a user scenario. User stories are easy to understand because they map to how the product actually behaves.

| Don't ask | How `by-usecase` asks | Reaction |
|--------------------|-----------------------|----------|
| "What's the JWT expiry?" | "How long can a user stay away and still open the app without logging in again?" | Instant: "About a week" |
| "Access token + refresh token, or session?" | "After how long unused should they re-enter their password?" | Instant: "A month" |
| "RBAC or ABAC?" | "Which actions are admin-only? Can regular users see admin-only things?" | Instant: "Admins see everything, users see their own" |
| "WebSocket or polling?" | "After an admin changes a setting, how soon should users see it? Do they need to restart?" | Instant: "They need to restart" |

The agent then **derives the technical design from the scenario answers**: "stay signed in for a week" → access token 7 days; "re-login after a month" → refresh token 30 days. Every technical decision in the spec links back to the scenario that produced it.

## How It Works

```
Phase 1: Context Scan  →  Phase 2: Domain & Scenario  →  Phase 3: Completeness  →  Phase 4: Output
(scan codebase)  (interview scenarios by domain)  (gap & conflict review)  (scenario list + tech derivation)
```

Four phases: scan the existing codebase for context (skip on greenfield), run the scenario interview domain by domain, review for gaps and conflicts, then emit one document with two parts — the **user scenario list** in business language, and the **technical derivation** with every decision traced to a scenario ID.

Full details in [`skills/by-usecase/SKILL.md`](./skills/by-usecase/SKILL.md).

## Skills

| Skill | What it does |
|-------|-------------|
| [`by-usecase`](./skills/by-usecase) | Scenario-driven requirements interview. Asks in **user scenarios, not technical jargon** — then derives the technical design from their answers. |

## Install

```bash
# List available skills
npx skills add douglas-ou/skills --list

# Install a specific skill
npx skills add douglas-ou/skills --skill by-usecase

# Install all skills
npx skills add douglas-ou/skills --all
```

Requires Node.js for `npx`. After install, the skill is picked up automatically by your agent (Claude Code, Cursor, Codex, …).

## Layout

```text
skills/
  <skill-name>/
    SKILL.md
    references/   # optional supporting docs
```

Add new skills under `skills/` — each folder with a `SKILL.md` is installable via the CLI.

## License

MIT — see [LICENSE](./LICENSE).
