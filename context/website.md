# Website Structure & Behaviour

## Theme / CSS
- **Background:** #111 (dark) | **Accent:** #e8a020 (gold/amber)
- **Nav:** #0d0d0d with 3px gold bottom border, sticky
- **Font:** Segoe UI | **Border:** #2a2a2a
- **File:** style.css

## Nav Brand (all pages)
```html
<img src="images/header_profile.jpg"> <!-- nav small photo -->
Sachin Desai / 3D/2D Animation and Technical Artist
```

## Video Behaviour
- **Desktop (>768px):** YouTube iframes autoplay (muted, looped) via JS on DOMContentLoaded
- **Mobile (≤768px):** YouTube thumbnail shown, tap play button to load iframe
- Detection: `window.innerWidth <= 768` only (NOT maxTouchPoints)
- Projects page: thumbnails always + click to play (other people's videos = ads risk)

## Mobile Menu
- Hamburger toggles `.nav-links.open`
- Closes on: link tap OR tap outside nav

## About Page Layout
- Two-column: circular photo left + bio text right
- Photo: `images/profile.jpg` (laser tag photo)
- Nav photo: `images/header_profile.jpg` (blue t-shirt photo)
- Footer strip: Contact | Follow Me (LinkedIn) — Download section REMOVED (buttons above)
- Download buttons: side-by-side on mobile

## File Structure
```
sachindesai7.github.io/
├── index.html          3D Animation homepage
├── tech-art.html       Pipeline tools + demoreel
├── 2d-animation.html   Spine + Unity animations
├── projects.html       14 shipped titles
├── about.html          Bio + resume download
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
3D/2D animator, rigger & technical artist since 2006.
Ex-EA. Ex-Ubisoft Abu Dhabi. Currently at Lila Games, Bangalore on Extraction Shooter (LILA Black).
Animated beasts, wrestlers, Disney heroes, TV show characters.
