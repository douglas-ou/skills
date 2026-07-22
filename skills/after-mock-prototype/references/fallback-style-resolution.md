# Fallback Style Resolution

Use this guide only when rendered or built evidence cannot be obtained.

## Static resolution order

Resolve each value from the first available source:

1. authored component markup and inline styles;
2. imported global CSS, Sass/Less, or CSS Modules;
3. theme files, CSS variables, token JSON, or component-library configuration;
4. framework configuration and lockfile-pinned framework defaults;
5. tests, stories, snapshots, and repository screenshots;
6. browser defaults or a measured approximation.

Keep the original cascade order. Resolve `var()` aliases recursively and retain their fallback values. For preprocessors, follow imports and simple variables/mixins statically; do not claim generated output is exact when compilation was not observed.

## Common style systems

### Vanilla CSS and preprocessors

Follow imports from the flow entry point, then collect matching selectors plus inherited/base rules. Preserve media queries, pseudo selectors, keyframes, and `@font-face`. Classify verbatim authored rules as `exact`; classify hand-expanded mixins or arithmetic as `derived`.

### CSS Modules

Read the module imported by each component and preserve the local class definitions. A source local name mapped to a standalone stable class is `derived` unless the real generated class name is known. Record both the component import and module selector in provenance.

### Tailwind or utility CSS

Prefer the actual generated CSS. If unavailable, resolve only utilities that appear in the flow using the repository's Tailwind/config version and theme extensions. Values taken from a pinned, verified config are `derived`; do not use current internet defaults for an older or unknown version.

### CSS-in-JS

Read the component, theme provider, variants, and actual prop branch used by the scene. Preserve static rules and resolve theme lookups. Mark runtime-dependent interpolation as `derived` when its inputs are known, otherwise `approximate`.

### Component libraries

Use the installed version, local theme overrides, and source-visible props. Do not substitute a visually similar component from another library. Browser-default focus or form-control rendering is approximate unless the target runtime is fixed and verified.

## Approximation protocol

Create a stable ID such as `approx-profile-card-shadow`. In the affected prototype source, add a non-visible marker adjacent to the value:

```css
/* approximate:approx-profile-card-shadow */
.profile-card { box-shadow: 0 16px 48px rgb(0 0 0 / 14%); }
```

Add a matching manifest entry with:

- the same `id`;
- a concrete `reason`;
- `originalContext.path` when a relevant source exists;
- `originalContext.detail` describing what was known and what was missing.

Connect the affected region's `styleSources[]` entry through `classification: "approximate"` and `approximationId`. Keep the marker in Before/After source only; do not render approximation labels or badges.

## Build failure handling

Record the failed command and error summary in `source.build` in the manifest, then continue statically. Do not edit the project to make it build. If a value remains uncertain, choose the least visually disruptive value consistent with repository evidence and mark it approximate.
