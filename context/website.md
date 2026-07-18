# Website Structure & Behaviour

## Theme / CSS
- **Background:** #111 (dark) | **Accent:** #e8a020 (gold/amber)
- **Nav:** #0d0d0d with 3px gold bottom border, sticky
- **Font:** Segoe UI | **Border:** #2a2a2a
- **File:** style.css
- HTML pages reference `style.css?v=20260718b` and `i18n.js?v=20260718` to refresh cached site assets after this repositioning update

## Nav Brand (all pages)
```html
<img src="images/header_profile.jpg"> <!-- nav small photo -->
Sachin Desai / Senior Technical Artist · Rigging Artist · Gameplay Animator
```
- Brand/home link points to `index.html`
- Main nav order: About Me, Tech Art, 3D Animation, AI Lab, 2D Art & Design, Projects

## Video Behaviour
- **Desktop (>768px):** YouTube iframes autoplay (muted, looped) via JS on DOMContentLoaded
- **Mobile (≤768px):** YouTube thumbnail shown, tap play button to load iframe
- Detection: `window.innerWidth <= 768` only (NOT maxTouchPoints)
- Projects page: thumbnails always + click to play (other people's videos = ads risk)

## Mobile Menu
- Hamburger toggles `.nav-links.open`
- Closes on: link tap OR tap outside nav
- Nav links collapse at <=768px so the longer Technical Artist/Rigging/Game Animation title does not squeeze the tablet header
- Nav brand subtitle is hidden at <=480px to keep phone headers clean in both English and Japanese

## Language Switcher
- Shared script: `i18n.js`
- Uses `data-en` / `data-ja` attributes and supports `data-html="true"`
- Persists language in `localStorage` when available, but continues switching if browser storage is blocked

## Tech Art Page Sections
- Rigging & DCC Tools
- Engine & Unity Integration
- Pipeline Automation

## About Page Layout
- Two-column: circular photo left + bio text right
- Photo: `images/profile.jpg` (laser tag photo)
- Nav photo: `images/header_profile.jpg` (blue t-shirt photo)
- Footer strip: Contact | Follow Me (LinkedIn)
- Resume and cover-letter download buttons are removed from `index.html` and `about.html`; PDF files remain in `files/`

## File Structure
```
sachindesai7.github.io/
├── index.html          About Me home/landing page
├── 3d-animation.html   3D Animation work page
├── tech-art.html       Pipeline tools + demoreel
├── 2d-animation.html   Spine + Unity animations
├── projects.html       14 shipped titles
├── about.html          Legacy About Me URL (same content as home)
├── style.css           Global dark theme
├── MEMORY.md           AI agent index
├── context/            AI agent context files
├── images/
│   ├── profile.jpg         About page hero (laser tag)
│   ├── header_profile.jpg  Nav bar photo (blue t-shirt)
│   └── tronji.png          Tronji show thumbnail
└── files/
    ├── Sachin_Desai_Resume.pdf
    ├── Sachin_Desai_Cover_Letter.pdf
    ├── batch_fbx_exporter_pro.py
    ├── maya_lod_qem_purepy.py
    └── maya_virus_cleaner.py
```

## About Me Bio (current)
Senior Technical Artist · Rigging Artist · Gameplay Animator with 20+ years in games and animation.
Ex-EA, Ex-Ubisoft Abu Dhabi, and Lila Games, Bangalore.
Positioning emphasizes production-ready rigs, Maya/Python tools, Unity integration, FBX/LOD workflows, gameplay animation systems, and the bridge between art and engineering.
