# Bolt / v0 / Figma Make / Google Stitch Prompting Guide

## Overview
Full-stack and prompt-to-UI generators. They default to bloated boilerplate (auth, dark mode, settings pages, marketing sections you never asked for). The single biggest lever is scoping it down explicitly and listing what NOT to scaffold.

## Key principles
- Always specify: stack, version, scope, and an explicit "do not include" list.
- Lovable: design-forward — include visual/UX intent.
- v0: Vercel-native — specify if you need non-Next.js output.
- Bolt: full-stack — be explicit about frontend vs. backend vs. database boundaries.
- Figma Make: design-to-code — reference Figma component names directly.
- Google Stitch: prompt-to-UI for Google-native styling — add "match Material Design 3 guidelines."

## Template

```
Tool: [Bolt / v0 / Lovable / Figma Make / Stitch]

Stack:
- Framework: [Next.js 14 App Router / React + Vite / etc.]
- Styling: [Tailwind / CSS modules / etc.]
- State: [none / Zustand / Redux / etc.]
- Backend: [none / Express / tRPC / etc.]
- Database: [none / Postgres + Drizzle / etc.]

Build Exactly:
- [component or page 1]
- [component or page 2]

Do NOT Include:
- Authentication (any kind)
- Dark mode toggle
- Settings page
- Landing/marketing sections not explicitly listed above
- Analytics, telemetry, cookie banners
- Any feature not in the "Build Exactly" list

Visual/UX Intent:
[for Lovable: design direction in plain language]
[for Stitch: "match Material Design 3 guidelines"]
[for Figma Make: reference Figma component names]

Constraints:
- TypeScript strict
- Accessible by default (semantic HTML, alt text, aria-labels where needed)
- Mobile-first responsive: 375px, 768px, 1440px

Done When:
[binary condition — e.g., "the three components render and pass type-check with zero errors"]
```

## Anti-patterns
- "Build a SaaS app" → generates 30 files of boilerplate, none of it what you wanted
- No "Do NOT include" list → auth, dark mode, and settings page show up uninvited
- Vague visual intent ("modern, clean") → generic AI aesthetic
- No stack version pinning → mix of old and new patterns
