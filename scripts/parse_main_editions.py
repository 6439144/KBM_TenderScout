import re
from pathlib import Path

html = Path("docs/recon/alyawm_main_editions.html").read_text(encoding="utf-8")
links = re.findall(r'<a\s+[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', html, re.DOTALL)
out = []
for h, t in links:
    clean_t = re.sub(r'<[^>]+>', '', t).strip()
    if any(k in h.lower() or k in clean_t for k in ['pdf', 'download', 'flip', 'edition', 'إصدار', 'تحميل', 'عدد', 'المناقصات']):
        out.append(f"{h} ---> {clean_t}")

Path("docs/recon/main_edition_links.txt").write_text("\n".join(out), encoding="utf-8")
print(f"Extracted {len(out)} relevant edition links.")
