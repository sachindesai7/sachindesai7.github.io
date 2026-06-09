# Tech Stack & Development Notes

## Stack
- **Pure HTML5 / CSS3 / Vanilla JavaScript** — no frameworks
- **Hosting:** GitHub Pages (static site, no backend needed)
- **No build process** — files uploaded directly to GitHub repo

## CSS Architecture
- Single `style.css` for global styles
- Page-specific styles in `<style>` blocks inside each HTML file
- CSS variables in `:root` for theming

### Key CSS Variables
```css
:root {
  --bg: #111;          /* page background */
  --bg2: #1a1a1a;      /* card/section background */
  --accent: #e8a020;   /* gold/amber accent */
  --text: #e0e0e0;     /* body text */
  --muted: #888;       /* secondary text */
  --border: #2a2a2a;   /* borders */
}
```

## JavaScript Patterns
- `toggleNav()` — hamburger menu open/close
- `playVideo(el, videoId)` — replaces thumbnail with YouTube iframe on click
- `DOMContentLoaded` → auto-detect desktop (>768px) → replace thumbnails with autoplay iframes
- Menu auto-close: click on link OR click outside nav

## Maya Tools (Tech Art page)
| Tool | GitHub file | Description |
|---|---|---|
| FBX Exporter | batch_fbx_exporter_pro.py | Batch export Maya assets to FBX |
| LOD Generator | maya_lod_qem_purepy.py | Auto-generate LOD meshes (pure Python, no plugins) |
| Virus Cleaner | maya_virus_cleaner.py | Remove Maya file viruses |
| Figma Asset Exporter | figma_exporter/ (zip on Drive) | Export Figma/FigJam images to local folders, no API token |

- Download links use direct file hosting: `files/filename.py` with `download` attribute
- GitHub view links: `https://github.com/sachindesai7/maya-tools/blob/main/filename.py`

## YouTube Embed Strategy
```
Projects page:   Autoplay iframes (own 15-sec recordings, no audio) → no ads
Index/Tech/2D:   Desktop=autoplay iframe | Mobile=thumbnail+click
Watch links:     Original full videos on YouTube (may have ads)
```

## Responsive Breakpoints
- `≤768px` — project rows stack vertically, video width 100%
- `≤640px` — hamburger menu shown, grid single column
- Portrait mobile — thumbnails shown (no autoplay black box issue)
- Landscape/desktop — autoplay active

## GitHub Pages Deployment
- Push to `main` branch → auto-deploys in ~1-2 minutes
- Upload method: GitHub web UI drag-and-drop (no git CLI used)
- 16 deployments completed as of session end

## Known Issues / Notes
- Tronji YouTube thumbnail unavailable → local `images/tronji.png` used as fallback
- YouTube autoplay requires `mute=1` in browsers
- `controls=0` used on projects page player videos for cleaner loop effect
