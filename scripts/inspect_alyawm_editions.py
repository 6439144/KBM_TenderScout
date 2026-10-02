import re
from pathlib import Path

html = Path("docs/recon/alyawm_main_editions.html").read_text(encoding="utf-8")
text = re.sub(r'<[^>]+>', ' ', html)
clean_lines = [l.strip() for l in text.splitlines() if l.strip()]
Path("docs/recon/main_edition_text.txt").write_text("\n".join(clean_lines[:150]), encoding="utf-8")
print(f"Extracted {len(clean_lines)} text lines from main editions.")
