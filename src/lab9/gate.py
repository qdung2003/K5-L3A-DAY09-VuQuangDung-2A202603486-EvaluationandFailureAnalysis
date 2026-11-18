"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems: list[str] = []
    for mid, val in (pr.get("metrics") or {}).items():
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            problems.append(f"{mid} is NaN or inf")
    manifest = pr.get("manifest") or {}
    expected_rows = int(manifest.get("items") or 0) * len(manifest.get("seeds") or [])
    rows = pr.get("rows") or []
    if len(rows) != expected_rows:
        problems.append(f"row count {len(rows)} != items x seeds {expected_rows}")
    pr_keys = {(r.get("item_id"), r.get("seed")) for r in rows}
    base_keys = {(r.get("item_id"), r.get("seed")) for r in base.get("rows") or []}
    if pr_keys != base_keys:
        problems.append("item/seed set differs from the baseline")
    if pr.get("evaluator_failures"):
        problems.append("evaluator_failures is not empty")
    graded = [m["id"] for m in spec.get("metrics") or []]
    for row in rows:
        for mid in graded:
            if mid in row and row[mid] is None:
                problems.append(f"{row.get('item_id')}@{row.get('seed')} {mid} is None")
                break
    pr_slices = {}
    base_slices = {}
    for row in rows:
        pr_slices.setdefault(row.get("item_id"), tuple(row.get("slices") or []))
    for row in base.get("rows") or []:
        base_slices.setdefault(row.get("item_id"), tuple(row.get("slices") or []))
    if pr_slices != base_slices:
        problems.append("slice tags differ from the baseline")
    if base_spec is not None and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        problems += _ratchet(spec, base_spec)
    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for sl in spec.get("slices") or []:
        name, metric = sl["name"], sl["metric"]
        a = per_item(pr, metric, slice_name=name)
        b = per_item(base, metric, slice_name=name)
        if not a:
            lines.append(f"  slice:{name}/{metric:<14} missing")
            if sl.get("blocking"):
                blocked.append(f"slice:{name}/{metric}")
            continue
        val = sum(a.values()) / len(a)
        verdict, note = "ok", ""
        if "min" in sl and val < sl["min"]:
            verdict = "fail"
        if sl.get("no_significant_drop"):
            keys = sorted(set(a) & set(b))
            if keys:
                d, lo, hi = stats.paired_bootstrap(
                    [a[k] for k in keys], [b[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                )
                note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                if hi < 0:
                    verdict = "fail"
        sid = f"slice:{name}/{metric}"
        if verdict != "ok" and sl.get("blocking"):
            blocked.append(sid)
        label = "ok" if verdict == "ok" else ("BLOCK" if sl.get("blocking") else "warn")
        lines.append(f"  {sid:<32} {val:<8.3f} {note:<28} {label}")
    return blocked, lines


def _threshold(metric: dict) -> dict:
    return metric.get("threshold") or {}


def _ratchet(spec: dict, base_spec: dict) -> list[str]:
    problems = []
    base_metrics = {m["id"]: m for m in base_spec.get("metrics") or []}
    new_metrics = {m["id"]: m for m in spec.get("metrics") or []}
    for mid, old in base_metrics.items():
        if mid not in new_metrics:
            problems.append(f"ratchet: metric {mid} disappeared")
            continue
        new = new_metrics[mid]
        old_th, new_th = _threshold(old), _threshold(new)
        if "max" in old_th and ("max" not in new_th or new_th["max"] > old_th["max"]):
            problems.append(f"ratchet: {mid} max loosened")
        if "min" in old_th and ("min" not in new_th or new_th["min"] < old_th["min"]):
            problems.append(f"ratchet: {mid} min loosened")
        if old.get("blocking") and not new.get("blocking"):
            problems.append(f"ratchet: {mid} no longer blocking")
        if old_th.get("no_significant_drop") and not new_th.get("no_significant_drop"):
            problems.append(f"ratchet: {mid} dropped no_significant_drop")
    base_slices = {s["name"]: s for s in base_spec.get("slices") or []}
    new_slices = {s["name"]: s for s in spec.get("slices") or []}
    for name, old in base_slices.items():
        if name not in new_slices:
            problems.append(f"ratchet: slice {name} disappeared")
            continue
        new = new_slices[name]
        if "min" in old and ("min" not in new or new["min"] < old["min"]):
            problems.append(f"ratchet: slice {name} min loosened")
        if old.get("blocking") and not new.get("blocking"):
            problems.append(f"ratchet: slice {name} no longer blocking")
        if old.get("no_significant_drop") and not new.get("no_significant_drop"):
            problems.append(f"ratchet: slice {name} dropped no_significant_drop")
    return problems


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
