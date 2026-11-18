"""Write a one-page demo of the eval reports. No extra dependencies.

    python -m lab9.demo_ui
    python -m lab9.demo_ui --open
"""

from __future__ import annotations

import argparse
import json
import webbrowser
from pathlib import Path

OUT = Path("reports/demo.html")
FILES = [
    "reports/baseline_v1.json",
    "reports/eval_fixed.json",
    "reports/eval_seeded_regression.json",
    "reports/baseline_v2.json",
    "reports/eval_slice_regression.json",
]


def load() -> list[dict]:
    reports = []
    for name in FILES:
        path = Path(name)
        if path.is_file():
            reports.append(json.loads(path.read_text(encoding="utf-8")))
    if not reports:
        raise SystemExit("no reports in reports/; run lab9.eval first")
    return reports


def render(reports: list[dict]) -> str:
    data = json.dumps(reports, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>LogiX-VN · Lab 9 eval</title>
<style>
  :root {{ color-scheme: dark; --bg:#12151c; --card:#1c2230; --line:#2c3548; --text:#e7ecf5; --muted:#93a0b8; --ok:#3dd68c; --bad:#ff6b6b; }}
  body {{ margin:0; font:15px/1.45 ui-sans-serif, Segoe UI, sans-serif; background:var(--bg); color:var(--text); }}
  header {{ padding:28px 32px 8px; }}
  h1 {{ margin:0 0 4px; font-size:22px; font-weight:600; }}
  p {{ margin:0; color:var(--muted); }}
  main {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:16px; padding:20px 32px 40px; }}
  article {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px 16px 8px; }}
  h2 {{ margin:0 0 4px; font-size:16px; }}
  .meta {{ color:var(--muted); font-size:12px; margin-bottom:12px; }}
  table {{ width:100%; border-collapse:collapse; }}
  td {{ padding:6px 0; border-top:1px solid var(--line); }}
  td:last-child {{ text-align:right; font-variant-numeric:tabular-nums; }}
  .good {{ color:var(--ok); }} .bad {{ color:var(--bad); }}
</style>
</head>
<body>
<header>
  <h1>LogiX-VN · Evaluation demo</h1>
  <p>Số lấy từ report do lab9.eval ghi. Không gõ tay.</p>
</header>
<main id="board"></main>
<script>
const reports = {data};
const safety = new Set(["approval_bypass", "secret_leak"]);
const board = document.getElementById("board");
for (const rep of reports) {{
  const card = document.createElement("article");
  const rows = Object.entries(rep.metrics).map(([k, v]) => {{
    const bad = safety.has(k) ? v !== 0 : (typeof v === "number" && v < 0.85 && k !== "cost_per_success");
    return `<tr><td>${{k}}</td><td class="${{bad ? "bad" : "good"}}">${{v}}</td></tr>`;
  }}).join("");
  card.innerHTML = `<h2>${{rep.shape}}</h2><div class="meta">${{rep.run_id}} · ${{rep.manifest.items}} item × ${{rep.manifest.seeds.length}} seed · ${{rep.manifest.llm}}</div><table>${{rows}}</table>`;
  board.appendChild(card);
}}
</script>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="lab9.demo_ui")
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(load()), encoding="utf-8")
    print(f"wrote {out}")
    if args.open:
        webbrowser.open(out.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
