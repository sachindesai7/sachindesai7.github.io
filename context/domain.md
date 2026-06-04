# Domain & Hosting

## Current Setup
- **Live URL:** https://sachindesai7.github.io
- **Hosting:** GitHub Pages (FREE)
- **SSL/HTTPS:** Auto-enabled by GitHub (FREE)
- **CDN:** GitHub uses Fastly CDN (FREE)
- **Repo:** https://github.com/sachindesai7/sachindesai7.github.io

## Old Setup (Wix — expires Nov 2026)
- **Domain:** sachindesai7.com (registered through Wix)
- **Cost:** ₹13,000/year (hosting + domain + SSL + CDN all bundled)
- **Expiry:** November 2026
- **Action needed:** Transfer domain out of Wix before renewal

## Planned New Domain
| Option | Registrar | Cost | Status |
|---|---|---|---|
| sachindesai.art | Porkbun | $88/5yr (~₹7,315) | Considering |
| sachin-desai.com | Cloudflare | $52/5yr (~₹4,340) | Available |
- Note: Cloudflare does NOT support .art TLD
- Recommendation: Porkbun for .art, Cloudflare for .com

## Cost Comparison
```
Old (Wix):              ₹13,000/year
New (GitHub Pages):     ₹0/year
New domain only:        ₹760–1,500/year
────────────────────────────────────
Saving:                 ₹11,500+/year
Over 5 years:           ₹57,500+ saved
```

## Connecting Custom Domain to GitHub Pages (when ready)
1. Buy domain (Porkbun/Namecheap/Cloudflare)
2. Add DNS A records pointing to GitHub IPs:
   - 185.199.108.153
   - 185.199.109.153
   - 185.199.110.153
   - 185.199.111.153
3. Add CNAME: www → sachindesai7.github.io
4. GitHub repo → Settings → Pages → Custom domain → enter domain
5. Wait 24–48 hours
