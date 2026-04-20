# CODEX.md

## NewsUTD Homepage Direction

The NewsUTD home screen must keep an **Arbitra-like visual language**:

- dark terminal-market palette (`#0a1014`, deep slate surfaces, green accent)
- mono utility typography for labels/tickers/buttons
- bold brand lockup with a boxed first letter (`N` + `EWSUTD`)
- top and bottom moving ticker rails
- one dominant CTA (`Enter Signal Console`)
- minimal clutter and strong first-screen hierarchy
- no gradients in homepage visuals (flat fills + borders only)
- ticker rails should visibly move by default

## UI Rules For This Repo

1. Keep `/` as the branded hero/entry page.
2. Keep `/monitor` as the full live dashboard.
3. Do not replace the Arbitra-style hero with a generic card/grid landing layout.
4. Maintain restrained motion; respect `prefers-reduced-motion`.
5. Preserve mobile readability (single-column fallback where needed).
6. Keep styling modern SaaS-distinctive: clear product panel, status indicators, and strong typographic hierarchy.

## Data + Behavior Rules

- Homepage may show lightweight live stats from backend endpoints.
- Do not remove or rewrite the existing LLM assistant behavior in monitor mode.
- Keep Pydantic, PostgreSQL cache, and pandas enhancements active and visible in copy or stats.

## Implementation Preference

For homepage changes, update these first:

- `frontend/src/components/HomePage.jsx`
- `frontend/src/styles/home.css`
- `frontend/src/App.jsx` (only if route flow changes)

Then run:

- `npm run build` in `frontend`
