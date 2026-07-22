# Review Bundle Contract

This contract defines the files, URL protocol, manifest, comparison behavior, and validation expectations.

## Required files

```text
<bundle>/
├── before.html
├── after.html
├── comparison.html
├── prototype-manifest.json
├── assets/
└── screenshots/
```

Use only local relative references for project images, fonts, and SVGs. The only expected remote runtime dependencies are these fixed files:

- `https://unpkg.com/react@18.3.1/umd/react.development.js`
- `https://unpkg.com/react-dom@18.3.1/umd/react-dom.development.js`
- `https://unpkg.com/@babel/standalone@7.29.0/babel.min.js`

## Page query protocol

Both prototype pages must read `URLSearchParams` and accept:

- `scene`: one value from `protocol.scenes`;
- `theme`: one value from `protocol.themes`, only when that array exists;
- `lang`: one value from `protocol.langs`, only when that array exists.

Unknown values fall back to the first declared value. The two pages must contain identical protocol declarations in:

```html
<script id="prototype-config" type="application/json">
{
  "scenes": ["profile", "detecting", "ready"],
  "themes": ["light", "dark"],
  "langs": ["zh-CN", "en-US"]
}
</script>
```

Omit `themes` or `langs` when unsupported. Do not emit fake single-value selectors for unsupported capabilities.

## Manifest shape

Use schema version `1.0.0`:

```json
{
  "schemaVersion": "1.0.0",
  "flow": {
    "id": "onboarding",
    "name": "Onboarding",
    "intent": "Clarify progress and readiness"
  },
  "source": {
    "root": "/absolute/path/to/repository",
    "gitRevision": "0123456789abcdef",
    "build": { "status": "rendered", "command": "npm run dev" }
  },
  "files": {
    "before": "before.html",
    "after": "after.html",
    "comparison": "comparison.html",
    "assets": "assets",
    "screenshots": "screenshots"
  },
  "protocol": {
    "scenes": ["profile", "detecting", "ready"],
    "themes": ["light", "dark"],
    "langs": ["zh-CN", "en-US"],
    "viewports": [
      { "id": "desktop", "width": 1440, "height": 900 },
      { "id": "mobile", "width": 390, "height": 844 }
    ]
  },
  "states": [
    { "scene": "profile", "theme": "light", "lang": "zh-CN" }
  ],
  "regions": [
    {
      "id": "profile-card",
      "componentSources": ["src/onboarding/ProfileCard.tsx"],
      "styleSources": [
        {
          "path": "dist/assets/app.css",
          "classification": "exact",
          "context": ".profile-card and responsive rules"
        }
      ],
      "tokenSources": ["src/styles/tokens.css#--surface"],
      "resourceSources": ["src/assets/profile.svg"]
    }
  ],
  "approximations": [],
  "screenshots": [
    {
      "file": "screenshots/before-profile-desktop.png",
      "page": "before",
      "scene": "profile",
      "theme": "light",
      "lang": "zh-CN",
      "viewport": "desktop"
    }
  ]
}
```

`states` must contain the full Cartesian product of scenes and each supported theme/language. Omit the corresponding key when a capability is unsupported.

Each region must contain all four source arrays, even when one is empty. Every style source needs `path`, `classification`, and `context`. `classification` is one of `exact`, `derived`, or `approximate`. Add `derivation` for derived sources. Add `approximationId` for approximate sources.

Every approximation ID must exist in top-level `approximations` with `reason` and `originalContext`. Mark its affected CSS or JSX non-visibly with `approximate:<id>` so the validator can prove that all approximated values are declared.

## Comparison behavior

- Populate controls from the embedded manifest snapshot.
- Apply an identical `URLSearchParams` object to Before and After iframe URLs.
- Set iframe CSS pixel width and height to the selected manifest viewport before scaling its wrapper with `transform: scale(...)`.
- Never use the visible comparison panel width as a responsive input to the prototype.
- Use a narrow-screen tab control to select Before or After.
- Do not render provenance or approximation warnings; the manifest is the audit surface.

## Screenshot contract

Record PNG captures in the manifest. The PNG pixel dimensions must equal the declared viewport. At minimum, cover both pages and every declared viewport, and ensure every scene appears somewhere in the capture set. Use the first theme/language as the canonical capture when a full matrix would be excessive.

Recommended filenames are:

```text
screenshots/<page>-<scene>[-<theme>][-<lang>]-<viewport>.png
```

## Repeated-run lifecycle

- Always replace Before with a fresh source-derived representation.
- Create After only when absent.
- Patch an existing After by region; never recopy the template or Before over it.
- Refresh comparison and manifest when the protocol or provenance changes.
- Regenerate screenshots after any visible Before or After change.
