---
name: claude-code-frontend-design
description: Senior frontend engineering judgment for framework apps (React, Next.js, Vue, Svelte, Angular, Solid). Use when building or changing UI components, pages, forms, state, data fetching, routing, styling, or when reviewing frontend code. Covers component boundaries, state placement, accessibility, performance, and verifying the change in a real browser.
---

# Frontend engineering

Write frontend code the way a senior engineer on the team would: consistent with what's
already there, accessible by default, and checked in a browser before calling it done.

## Before writing code

1. **Read the house style.** Find two or three existing components similar to what you're
   building. Match their file layout, naming, styling approach (CSS modules, Tailwind,
   styled-components...), data fetching library, and test style. Do not introduce a new library
   for something the codebase already does.
2. **Check the framework version and mode.** App Router vs Pages Router, server vs client
   components, Vue 2 vs 3, Svelte 4 vs 5 runes. Advice that's right for one is wrong for the other.
3. **Find the design tokens.** Use existing spacing, color, and type tokens or theme values.
   Hard-coded hex values and pixel sizes are a smell.

## Components

- One component, one job. Split when a file mixes data loading, layout, and interaction logic.
- Props describe what, not how: `variant="danger"` over `color="#d00"`.
- Keep components controlled where a parent needs the value; uncontrolled otherwise.
- Avoid prop drilling deeper than two levels; reach for composition (children, slots) before
  context or a global store.
- Render lists with stable keys from the data, never the array index if items can reorder.

## State

Put state at the lowest level that needs it, and pick the right kind:

| Kind | Where |
|---|---|
| Server data | the app's data library (React Query, SWR, loaders, server components) |
| URL-shareable (filters, tabs, page) | the URL |
| Form input | the form library or local state |
| Ephemeral UI (open, hover) | local state |
| Truly global (auth user, theme) | context or store |

Derive values instead of syncing them with effects. An effect that sets state from props is
usually a bug waiting to happen.

## Data and async

- Handle every state: loading, empty, error, and success. Design the empty and error states,
  don't leave them blank.
- Cancel or ignore stale requests (AbortController, the library's built-in handling).
- Never fetch in a loop of components when one request at the parent would do.
- Validate data at the boundary if it comes from outside the app.

## Accessibility (not optional)

- Use the semantic element first: `button` for actions, `a` for navigation, `label` tied to
  every input, headings in order.
- Everything interactive works with the keyboard and has a visible focus style.
- Images get meaningful `alt` or `alt=""` if decorative.
- Dialogs trap focus and return it on close; use the codebase's existing dialog primitive.
- Don't convey meaning with color alone. Check contrast for text against its background.

## Performance

- Measure before optimizing. Don't sprinkle `memo`/`useMemo` without a reason.
- Watch for the common real costs: large dependencies in the client bundle, unoptimized images,
  layout shift from unsized media, waterfalls of sequential requests, re-rendering long lists
  (virtualize past a few hundred rows).
- Lazy-load heavy, below-the-fold, or rarely used routes and components.

## Styling and layout

- Mobile first; check at a narrow width (about 375px) and a wide one.
- Support the app's dark mode if it has one.
- Prefer layout with flex/grid and gap over margins on children.

## Verifying

Type checks and unit tests are not enough for UI. Before saying it's done:

1. Run the type checker, linter, and the tests near the code you changed.
2. Open the page in a browser (the dev server, or a Playwright/Storybook check if the project
   has one). Click through the change, including the empty and error states, and tab through it
   with the keyboard.
3. Check the browser console for errors and warnings you introduced.
4. Report what you verified and what you could not, plainly.
