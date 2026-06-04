# AGENTS.md — AI Agent Onboarding

> **Any AI tool opening this repo: READ THIS FIRST, then read `MEMORY.md`.**
> This is the portfolio website of **Sachin Desai** (3D/2D Animator · Rigger · Technical Artist).
> Live site: https://sachindesai7.github.io · auto-deploys from `main` via GitHub Pages.

---

## 1. Start here (load order)

1. **`MEMORY.md`** — token-saving index. Quick facts + which context file to read for what.
2. **`context/*.md`** — load only the one(s) relevant to the task:
   - `context/website.md` — page structure, CSS theme, mobile behaviour, layout
   - `context/videos.md` — every YouTube video ID (player + watch links)
   - `context/tech-stack.md` — HTML/CSS/JS details, file structure, deployment
   - `context/domain.md` — hosting, domain migration plan, costs

Do **not** read every file blindly — that wastes tokens. Use `MEMORY.md` to decide.

## 2. What this project is

- **Pure static site**: HTML5 + CSS3 + vanilla JavaScript. **No frameworks, no build step.**
- **5 pages**: `index.html` (3D), `tech-art.html`, `2d-animation.html`, `projects.html`, `about.html`
- **Global styles**: `style.css`. Page-specific styles live in `<style>` blocks inside each page.
- **Hosting**: GitHub Pages (free). Push to `main` → live in ~1–2 minutes.

## 3. House rules (do not break these)

- **Theme**: background `#111`, accent gold `#e8a020`, text `#e0e0e0`, font Segoe UI. Use the CSS variables in `:root` — never hard-code new colors.
- **Videos**: desktop (>768px) autoplays muted/looped iframes; mobile (≤768px) shows a thumbnail + tap-to-play. Detection uses `window.innerWidth <= 768` only. Keep this pattern — it exists to avoid ads and mobile black-box issues.
- **Projects page videos**: always thumbnail + click (they include other people's footage = ad risk).
- **Mobile menu**: hamburger toggles `.nav-links.open`; closes on link tap or tap outside.
- **Don't add dependencies** (no React, no npm, no Tailwind). Keep it plain and framework-free.

## 4. Required workflow for ANY change

1. Make the edits, matching existing conventions above.
2. **Update the knowledge base** so it never drifts from the real site:
   - New/changed video → `context/videos.md`
   - Layout/page/CSS change → `context/website.md`
   - Tooling/deploy change → `context/tech-stack.md`
   - Domain/hosting change → `context/domain.md`
   - Update the **"Last Updated"** date in `MEMORY.md`.
3. Commit and push to `main` (this deploys the live site).
4. Tell Sachin what changed and confirm it's live.

## 5. Git identity (important)

This repo is configured **locally** to commit as Sachin's **personal** identity:
`Sachin Desai <sachindesai7@gmail.com>` — NOT the office email. Leave it that way.
Do not change `--global` git config. Do not rewrite existing commit history.

## 6. Contact / ownership

- Owner: Sachin Desai · sachindesai7@gmail.com · +91-9820213275
- Repo: https://github.com/sachindesai7/sachindesai7.github.io
- LinkedIn: https://linkedin.com/in/sachindesai7
