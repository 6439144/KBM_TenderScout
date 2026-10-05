import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

content = open("output/reports/KBM_Tender_Dashboard.html", encoding="utf-8").read()
matches = [m.start() for m in re.finditer("LOADING", content)]
print(f"Total LOADING matches: {len(matches)}")
for pos in matches:
    print("--- CONTEXT ---")
    snippet = content[max(0, pos-100):min(len(content), pos+100)].replace("\n", " ")
    print(snippet)
