from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "report" / "SmartFind_Report.md"
text = source.read_text(encoding="utf-8")
words = re.findall(r"\b[\w]+(?:[-’'][\w]+)*\b", text)
print(f"Academic report word count: {len(words)}")
print(f"Requirement (> 3,000): {'PASS' if len(words) > 3000 else 'NOT MET'}")
