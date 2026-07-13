---
name: by-usecase
description: "Scenario-driven requirements interview for PMs and business stakeholders. Ask in user-scenario language only—never technical details—and derive the technical design from those answers. Triggers: usecase interview, by usecase, scenario interview, user scenarios, requirements alignment, use case analysis, business scenario mapping, derive requirements from scenarios."
---

# By Usecase: Scenario-Driven Requirements Interview

A requirements interview for product managers and business decision-makers. **Core rule: never ask technical questions—only talk about user scenarios.**

The agent derives the technical design from scenarios. Stakeholders do not need to know what JWT, REST APIs, or token expiry are. They only need to answer questions like: "If a user doesn't open the app for a week, what should happen when they come back?"

## Why This Skill

Problems with traditional requirements interviews:

| How you ask | Stakeholder reaction |
|-------------|----------------------|
| ❌ "What's the JWT expiry?" | They don't know what JWT is |
| ❌ "Access token + refresh token, or session?" | They can't make a technical choice |
| ✅ "How long can a user stay away and still open the app without logging in again?" | Instant answer: "About a week" |
| ✅ "After how long unused should they re-enter their password?" | Instant answer: "A month" |

**Derive tech from scenario answers**: stay signed in for a week → access token 7 days; re-login after a month → refresh token 30 days. Stakeholders never touch technical concepts.

---

## Workflow

```
Phase 1: Context Scan  →  Phase 2: Domain & Scenario  →  Phase 3: Completeness  →  Phase 4: Output
(scan codebase for context)  (interview scenarios by domain)  (completeness review)  (scenario list + tech derivation)
```

---

## Phase 1: Context Scan — Explore Code Context

### When to run

- Existing project / codebase → run this phase
- Greenfield project → skip; go straight to Phase 2

### What to explore

Use available tools (shell grep/find, codebase search, file reads) to quickly extract:

1. **Project structure**: directories, module boundaries
2. **Tech stack**: frameworks, languages (e.g. package.json, go.mod, pyproject.toml)
3. **Existing capabilities**: auth, data models, API endpoints, etc.
4. **Business domain clues**: infer domains from folder names, routes, model names

### Output

Show the user a short overview in **business language**, not technical jargon:

```
Project overview:
- Product type: [desktop app / web app / API service]
- Existing capabilities: [list user-facing features]
- Business domains involved: [user management, settings, messaging, etc.]

Next I'll walk through user scenarios around these domains.
```

---

## Phase 2: Domain & Scenario Interview

This is the core phase. Two steps: identify domains, then interview scenarios per domain.

### Step 1: Identify business domains

From Phase 1 (or the user's brief), list the business domains involved.

Use ask/question tools if available to confirm the domain split with the user:

```
I've grouped things into these business domains:
1. User login & identity
2. AI configuration
3. Usage monitoring

Anything missing or that should be adjusted?
```

### Step 2: Interview scenarios per domain

Within each domain, identify key user scenarios and interview them one by one.

#### Scenario structure

Each scenario has four elements. Use ask/question tools if available to confirm them step by step:

1. **Actor**: Who is acting? (end user / admin / system)
2. **Trigger**: When does this happen?
3. **Expectation**: What should the user see or get?
4. **Failure**: If something goes wrong, how should it be handled?

#### Questioning principles

**Never ask technical questions.** Derive every technical decision from scenarios. Reference table:

| Technical decision | Don't ask | Ask instead |
|--------------------|-----------|-------------|
| Auth method | "JWT or session?" | "After logging in once, do they need to enter a password next time they open the app?" |
| Token lifetime | "How long should the access token live?" | "How many days can they stay away and still open the app without logging in?" |
| Password policy | "Min length and complexity?" | "What happens when they forget their password—admin reset or self-serve recovery?" |
| Permission model | "RBAC or ABAC?" | "Which actions are admin-only? Can regular users see admin-only things?" |
| Data sync | "WebSocket or polling?" | "After an admin changes a setting, how soon should users see it? Do they need to restart?" |
| Offline support | "Need Service Worker caching?" | "Can users keep working offline? Which features still work?" |
| Multi-device sync | "What consistency strategy?" | "If they change something on phone, should desktop see it immediately?" |
| Quotas | "Token bucket or sliding window?" | "What do users see when they hit their limit—hard stop or advance warning?" |
| Audit logging | "Need audit logs? At what granularity?" | "Do admins need to see who did what, and when?" |
| Version compatibility | "What's the API versioning strategy?" | "Can old clients still work? Will you force upgrades?" |

#### Scenario discovery dimensions

Cover scenarios along these axes:

1. **Lifecycle**: first use → daily use → change → exit
   - What's the first-time flow?
   - How do they use it day to day?
   - How do they change settings when needed?
   - How do they leave / deactivate / delete?

2. **Role differences**: different experiences by role
   - Do admins and end users see the same thing?
   - When an admin makes a change, how do end users notice?

3. **Time**: immediate → delayed → long-term
   - Do they see results right away?
   - What changes after some time?
   - What happens when data grows over a year?

4. **Failure paths**: error → recovery → edge cases
   - Wrong input?
   - Network down?
   - Two people editing the same thing at once?

#### Interview rhythm

- Use ask/question tools if available; ask 1–2 scenario-related questions at a time
- Offer concrete options to reduce typing burden
- Use named examples to make scenarios vivid ("Alex logs in Monday, opens again Friday...")
- Propose reasonable assumptions for confirmation instead of open-ended questions
- Finish one domain before moving to the next

---

## Phase 3: Completeness Review

After all domain interviews:

1. **Coverage summary**: list every confirmed scenario
2. **Gap check**: missing domains or edge scenarios?
3. **Conflict check**: any contradictions across scenarios?
4. **Priority**: which scenarios are MVP must-haves?

Use ask/question tools if available to get the user's final confirmation before writing output.

---

## Phase 4: Output — Scenario List + Technical Derivation

### Document structure

Produce one document with two parts:

**Part 1: User scenario list** (business language; shareable with PMs and stakeholders)

Organized by domain. Per-scenario format:

```markdown
## Domain: User Login & Identity

### S-001: First login
- **Actor**: End user
- **Trigger**: Admin created the account; user opens the app for the first time
- **Expectation**: Enter username/password and land on the main screen
- **Failure**:
  - Wrong password → show "Incorrect username or password" (don't reveal which)
  - Account disabled → show "Please contact an administrator"
- **Priority**: P0

### S-002: Returning soon (recently active)
- **Actor**: End user
- **Trigger**: User used the app within the last 7 days and opens it again
- **Expectation**: Land on the main screen without entering a password
- **Priority**: P0

### S-003: Returning after long inactivity
- **Actor**: End user
- **Trigger**: User has not opened the app for more than 30 days
- **Expectation**: Must re-enter username and password
- **Priority**: P1
```

**Part 2: Technical derivation** (auto-derived from scenarios; for the engineering team)

Every technical decision links back to scenario IDs:

```markdown
## Technical Derivation

### Authentication

| Decision | Value | Derived from |
|----------|-------|--------------|
| Auth method | JWT access token + refresh token | S-001 requires login; S-002 requires stay signed in; S-003 defines timeout boundary |
| Access token lifetime | 7 days | S-002: "open within 7 days without login" |
| Refresh token lifetime | 30 days | S-003: "re-login after 30 days unused" |
| Password hashing | Argon2id | S-001: password login (security best practice) |
| Error messaging | Unified "Incorrect username or password" | S-001 failure: don't reveal which field failed |
```

### Output rules

- Default path: `usecase-spec-[topic].md` (user may override)
- Part 1 in plain business language—no technical jargon
- Part 2 ties every decision to scenario IDs so it is traceable
- Decisions not confirmed in scenarios: mark as "Default recommendation" and state the reason

### Template

Full template: `references/output-template.md`.
