---
name: after-mock-prototype
description: Create source-faithful, high-fidelity Before/After review mocks for one user flow by inspecting an existing repository, its rendered DOM, and its real CSS. Use when the user asks for a high-fidelity mock, a Before/After prototype, a redesign based on source styles, 按源码样式制作改版稿, 高保真 mock, before/after 原型, or wants to adjust an After mock and review multiple states. Generate a standalone review bundle without changing production code.
---

# After Mock Prototype

Build a review-only bundle for one user flow. Refresh `before.html` from current source, preserve and incrementally edit `after.html`, and compare both across the same scenes, themes, languages, and real viewport sizes.

## Non-negotiable boundaries

- Treat the target repository as read-only except for the output directory.
- Write to `<target-repo>/design-demos/<flow-slug>/` unless the user specifies another review-only path.
- Do not edit production components, routes, APIs, tests, or build configuration.
- Do not require or invoke `frontend-prototype`; this skill is self-contained.
- Prefer traceability to invented polish. Classify every style decision as `exact`, `derived`, or `approximate`.
- Keep approximation details in `prototype-manifest.json`; never show them in `comparison.html`.

## Load the bundled guidance

1. Read [references/source-style-extraction.md](references/source-style-extraction.md) before exploring or extracting styles.
2. Read [references/review-contract.md](references/review-contract.md) before creating any bundle file.
3. Read [references/fallback-style-resolution.md](references/fallback-style-resolution.md) only when the app cannot render, built CSS is unavailable, or a value cannot be traced exactly.

Use [assets/prototype-template.html](assets/prototype-template.html) independently for `before.html` and `after.html`. Use [assets/comparison-template.html](assets/comparison-template.html) for `comparison.html`. Replace every `__UPPER_SNAKE_CASE__` placeholder; do not leave template markers in the bundle.

## Workflow

### 1. Explore the repository and flow

- Resolve the target repository, source root, git revision, flow intent, and output path.
- Follow route entry points into the visible components for the requested flow.
- Locate state machines, loading/error/empty/success variants, theme providers, i18n catalogs, responsive breakpoints, fonts, icons, images, and design tokens.
- Limit scope to the requested user flow, but include every materially different state required to review it.

### 2. Establish the review matrix

- Derive stable `scene` IDs from real flow states. Do not invent states only to fill the UI.
- Add `theme` only when the project supports multiple themes.
- Add `lang` only when the project supports multiple languages.
- Use project breakpoints to select viewports. Always include at least one desktop and one mobile viewport; default to `1440x900` and `390x844` only when the project provides no stronger evidence.
- Build the full scene/theme/language state matrix defined in the review contract.

### 3. Extract DOM, CSS, and assets

- Run or build the project when safe and practical, then capture the rendered DOM and the actual CSS rules that apply to the flow.
- Preserve source element structure, class names, inline styles, SVG markup, text, and asset hierarchy whenever they remain usable in a standalone page.
- Extract matching class rules, CSS variables, media queries, pseudo states/elements, keyframes, font faces, and supporting selectors from the project's actual CSS output. Do not substitute a generic stylesheet.
- Copy every required local image, font, and SVG into `assets/`, retaining sensible relative subpaths. Rewrite references to local relative paths.
- Prefer recombining existing classes, tokens, dimensions, and component patterns for After changes.

### 4. Refresh Before

- Rebuild `before.html` from current source on every run, even when the file already exists.
- Use fixed CDN versions: React `18.3.1`, ReactDOM `18.3.1`, and Babel Standalone `7.29.0`.
- Implement the shared query protocol and embed `#prototype-config` exactly as specified in the review contract.
- Represent only review-relevant behavior; do not reproduce backend calls or persistence.

### 5. Create or edit After

- If `after.html` does not exist, create it from the prototype template using the requested redesign intent. If the intent is insufficient, copy the completed Before representation as the initial After.
- If `after.html` exists, read it fully and patch only the affected regions. Never regenerate or overwrite the whole file, and preserve prior design decisions not contradicted by the new request.
- Reconcile After with newly refreshed shared assets or protocol changes through minimal edits.
- Keep scene semantics identical to Before. A scene may look different, but it must represent the same state.

### 6. Build the review bundle

Create exactly these core outputs:

```text
before.html
after.html
comparison.html
prototype-manifest.json
assets/
screenshots/
```

- Generate `comparison.html` from the bundled template and embed the manifest snapshot used by its controls.
- Send the same `scene`, optional `theme`, and optional `lang` parameters to both iframes.
- Size each iframe to the selected real viewport and visually scale its wrapper. Never let a comparison column become the iframe's responsive viewport.
- On narrow screens, show a Before/After tab switch instead of squeezing both frames side by side.
- Record region-level component, CSS, token, resource, and classification provenance in the manifest.
- Capture PNG screenshots for Before and After at every declared viewport. Cover every scene across the capture set and record each capture in the manifest.

### 7. Validate and inspect

Run:

```bash
python3 <skill-dir>/scripts/validate_bundle.py <output-dir>
```

Fix every reported error. Then:

- Open `comparison.html` through a local HTTP server.
- Exercise every scene/theme/language control and both viewport sizes.
- Run a Chromium smoke test when Chromium or Playwright is available; check the console and failed requests.
- Inspect desktop and mobile screenshots for clipping, incorrect responsive states, missing fonts/assets, and Before/After parameter drift.
- Run the validator again after the final After edit.

## Update behavior

On repeated invocations, report separately which facts came from current source and which After regions were preserved. If a build fails, continue with the static fallback, mark uncertainty precisely, and never silently upgrade `derived` or `approximate` evidence to `exact`.
