from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
INCLUDE = {".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".sql"}
EXCLUDE_PARTS = {"node_modules", ".next", "__pycache__", ".venv", "venv", "dist", "build", "release"}
total = 0; files = 0
for path in ROOT.rglob("*"):
    if not path.is_file() or path.suffix not in INCLUDE or any(part in EXCLUDE_PARTS for part in path.parts):
        continue
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        continue
    meaningful = [line for line in lines if line.strip() and not line.lstrip().startswith(("#", "//", "/*", "*"))]
    total += len(meaningful); files += 1
print(f"Meaningful source lines: {total}")
print(f"Source files counted: {files}")
