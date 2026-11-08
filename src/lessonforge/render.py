"""Human-readable outputs: the final lesson file and the rejection log."""
from __future__ import annotations

from .schemas import Attempt


def _cell(text: str, limit: int = 220) -> str:
    text = (text or "").replace("|", "\\|").replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 1] + "\u2026"


def check_delta(prev: Attempt, cur: Attempt) -> dict[str, list[str]]:
    before = {r.id for r in prev.evaluation.failed}
    after = {r.id for r in cur.evaluation.failed}
    return {
        "fixed": sorted(before - after),
        "newly_broken": sorted(after - before),
        "still_failing": sorted(before & after),
    }


def rejection_log_md(meta: dict, attempts: list[Attempt], final_number: int) -> str:
    total = len(attempts[0].evaluation.results) if attempts else 0
    status = meta["status"]
    headline = (f"PASSED on attempt {final_number} of {len(attempts)}" if status == "passed"
                else f"DID NOT PASS after {len(attempts)} attempts - best attempt ({final_number}) "
                     "sent for human review")
    lines = [
        f"# Rejection Log: {meta['topic']}",
        "",
        f"- **Run ID:** `{meta['run_id']}`",
        f"- **Result:** {headline}",
        f"- **Writer model:** `{meta['writer_model']}` | **Judge model:** `{meta['judge_model']}`",
        f"- **Rubric:** {total} hard pass/fail checks (no partial credit)",
        f"- **Learned rules applied from memory:** {len(meta.get('rules', []))}",
        *([f"- **Stopped early:** {_cell(meta['error'], 300)}"] if meta.get("error") else []),
        "",
        "## Summary",
        "",
        "| Attempt | Result | Checks passed | Failed checks |",
        "|---|---|---|---|",
    ]
    for a in attempts:
        ev = a.evaluation
        failed = ", ".join(r.id for r in ev.failed) or "-"
        lines.append(f"| {a.number} | {'PASS' if ev.passed else 'FAIL'} | "
                     f"{len(ev.results) - len(ev.failed)}/{len(ev.results)} | {failed} |")

    if meta.get("rules"):
        lines += ["", "## Learned rules used in this run (from memory)", ""]
        lines += [f"- {r}" for r in meta["rules"]]

    for i, a in enumerate(attempts):
        ev = a.evaluation
        lines += ["", f"## Attempt {a.number}: {'PASSED' if ev.passed else 'FAILED'}", ""]
        if a.injected_errors:
            lines.append(f"> Deliberately injected errors (demo): **{', '.join(a.injected_errors)}**")
            lines.append("")
        if i > 0:
            d = check_delta(attempts[i - 1], a)
            lines.append(f"**Check changes vs attempt {a.number - 1}:** fixed: {', '.join(d['fixed']) or '-'}; "
                         f"newly broken: {', '.join(d['newly_broken']) or '-'}; "
                         f"still failing: {', '.join(d['still_failing']) or '-'}")
            lines.append("")
            if a.changes:
                lines += ["**What the writer changed on this retry:**", "", a.changes.strip(), ""]
        if ev.failed:
            lines += ["| Check | Method | Why it failed | Evidence | Fix requested |", "|---|---|---|---|---|"]
            for r in ev.failed:
                ev_note = "" if r.evidence_verified is not False else " _(quote not found verbatim)_"
                lines.append(f"| **{r.id}** {r.name} | {r.method} | {_cell(r.reason)} | "
                             f"{_cell(r.evidence)}{ev_note} | {_cell(r.fix)} |")
        else:
            lines.append("All checks passed.")

    final = next(a for a in attempts if a.number == final_number)
    lines += ["", f"## Final scorecard (attempt {final_number})", "",
              "| Check | Dimension | Method | Result | Reason |", "|---|---|---|---|---|"]
    for r in final.evaluation.results:
        lines.append(f"| {r.id} {r.name} | {r.dimension} | {r.method} | "
                     f"{'PASS' if r.passed else 'FAIL'} | {_cell(r.reason, 160)} |")
    return "\n".join(lines) + "\n"
