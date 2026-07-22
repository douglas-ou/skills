# Source and Style Extraction

Use this procedure to make every visible decision traceable to the target repository.

## 1. Map the flow before reading leaf files

Trace the requested route from its registration point to the rendered screen and visible descendants. Record:

- router and route guards;
- screen and layout components;
- state sources and branches;
- theme and localization providers;
- global CSS entry points and build-time style configuration;
- icon, image, font, and illustration sources;
- desktop/mobile breakpoints and container queries.

Search for the exact route, distinctive UI copy, state enum values, and test selectors. Those usually identify the rendered path faster than directory names.

## 2. Prefer rendered evidence

When the project runs safely:

1. Start its documented development or preview command without changing dependencies or configuration.
2. Navigate to each scene using existing fixtures, query parameters, local storage, or mocked frontend state. Do not mutate a real backend.
3. Capture the rendered DOM for the flow, including generated class names and inline styles.
4. Walk `document.styleSheets` and keep rules whose selectors match the flow subtree or define inherited/global behavior it uses.
5. Retain enclosing `@media`, `@container`, `@supports`, and `@layer` blocks.
6. Retain referenced `@font-face` and `@keyframes` blocks, CSS custom property definitions, pseudo selectors, and selectors required for combinator context.
7. Confirm CSS Module or CSS-in-JS generated names against the rendered DOM rather than guessing hashes.

Cross-origin stylesheets may block `cssRules`. In that case, read the matching built CSS file from disk or retrieve the same-origin asset from the local build server.

## 3. Preserve structure before translating

- Keep semantically relevant element nesting and source order.
- Keep source `class`, `style`, ARIA, SVG, and data attributes unless they depend on unavailable runtime code.
- Copy source copy from i18n catalogs for each declared language.
- Inline authored SVG markup when practical. Copy larger SVG files into `assets/`.
- Replace API-driven data with stable local fixtures that preserve text length and layout behavior.
- Remove analytics, network mutations, authentication, and persistence.

Use React JSX in the standalone template even when the source framework differs. Translate syntax mechanically; do not redesign Before during translation.

## 4. Extract the actual CSS closure

Start with rules matching preserved classes, IDs, elements, and attributes. Expand the set to include:

- ancestor and sibling selectors needed for specificity;
- reset/base styles that affect the subtree;
- inherited typography and color;
- custom properties referenced through `var()` and their fallback chain;
- pseudo states and pseudo elements;
- media/container queries at project breakpoints;
- animations and their keyframes;
- font faces and local font files;
- assets referenced by `url()`.

Preserve rule order and specificity. Do not flatten responsive rules into a desktop snapshot. Do not replace project values with a utility framework's defaults when built CSS supplies the resolved value.

## 5. Classify provenance

Use one classification per style source entry:

- `exact`: copied verbatim from source or actual build output, with a path and selector/token context.
- `derived`: computed mechanically from exact project evidence, such as resolving a token alias or combining existing spacing tokens. Record the derivation.
- `approximate`: chosen because source and built evidence do not determine the value. Follow the fallback guide and attach an approximation ID.

Computed styles alone are normally `derived`: they prove the rendered result but may collapse cascade, inheritance, and browser defaults. A copied authored or built rule is `exact`.

## 6. Build After from existing language

First reuse the project's component patterns, classes, tokens, dimensions, icon family, and motion curves. Create new CSS only for the requested delta. When a new value cannot be expressed through project evidence, mark the smallest affected value—not the whole region—as approximate.
