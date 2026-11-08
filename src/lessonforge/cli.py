from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from .config import Settings
from .inject import ALL as INJECT_KINDS
from .inject import inject_errors
from .knowledge import TopicPack, find_topic_pack
from .memory import Memory
from .schemas import Evaluation

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

app = typer.Typer(help="LessonForge: self-evaluating lesson generator (generate -> evaluate -> regenerate).",
                  no_args_is_help=True, add_completion=False)
rules_app = typer.Typer(help="View or toggle learned prompt rules.", no_args_is_help=True)
rubric_app = typer.Typer(help="Review rubric proposals produced by reflection.", no_args_is_help=True)
app.add_typer(rules_app, name="rules")
app.add_typer(rubric_app, name="rubric")
console = Console()


def log(msg: str) -> None:
    style = "bold green" if "PASSED" in msg else "bold red" if "FAILED" in msg else (
        "magenta" if msg.startswith(("DEMO", "Reflection")) else "cyan")
    console.print(f"[dim]{datetime.now():%H:%M:%S}[/dim] [{style}]{escape(msg)}[/{style}]")


def _parse_kinds(value: Optional[str]) -> list[str] | None:
    if value is None:
        return None
    kinds = [k.strip() for k in value.split(",") if k.strip() and k.strip() != "all"]
    bad = [k for k in kinds if k not in INJECT_KINDS]
    if bad:
        raise typer.BadParameter(f"unknown kind(s) {bad}; choose from {INJECT_KINDS}")
    return kinds


def show_evaluation(ev: Evaluation, title: str) -> None:
    console.rule(f"[bold]{title}")
    for r in ev.results:
        mark = "[bold green]PASS[/bold green]" if r.passed else "[bold red]FAIL[/bold red]"
        console.print(f"{mark} [bold]{r.id}[/bold] {escape(r.name)} [dim]({r.method})[/dim]")
        console.print(f"     {escape(r.reason)}", style="dim" if r.passed else None, highlight=False)
        if not r.passed:
            if r.evidence:
                flag = " [yellow](quote not found in lesson)[/yellow]" if r.evidence_verified is False else ""
                console.print(f"     [magenta]evidence:[/magenta] {escape(r.evidence[:300])}{flag}", highlight=False)
            if r.fix:
                console.print(f"     [cyan]fix:[/cyan] {escape(r.fix[:300])}", highlight=False)
    verdict = "[bold green]SHIP IT[/bold green]" if ev.passed else (
        f"[bold red]REJECTED[/bold red] - {len(ev.failed)} of {len(ev.results)} checks failed")
    console.print(Panel(verdict, expand=False))


@app.command()
def run(
    topic: str = typer.Option("Introduction to RAG", "--topic", "-t", help="Lesson topic."),
    max_retries: Optional[int] = typer.Option(None, help="Max regenerations (default from .env, usually 2)."),
    inject_error: Optional[str] = typer.Option(
        None, "--inject-error", help=f"Demo: corrupt attempt 1 on purpose. Comma list of {INJECT_KINDS} or 'all'."),
    no_memory: bool = typer.Option(False, help="Do not read or write memory."),
    no_rules: bool = typer.Option(False, help="Ignore learned rules (baseline comparison)."),
) -> None:
    """Run the full agentic loop and write the lesson + rejection log to outputs/."""
    from .factory import make_deps
    from .graph import new_run_id, run_pipeline

    s = Settings()
    if max_retries is not None:
        s.max_retries = max_retries
    deps = make_deps(s, inject=_parse_kinds(inject_error), use_memory=not no_memory,
                     use_learned_rules=not no_rules, log=log)
    run_id = new_run_id()
    console.print(Panel(f"[bold]LessonForge[/bold]  topic: {topic}\nrun: {run_id}\n"
                        f"writer: {s.writer_model}  judge: {s.judge_model}  max retries: {s.max_retries}",
                        expand=False))
    state = run_pipeline(topic, deps, run_id)
    from .schemas import Attempt

    attempts = [Attempt.model_validate(a) for a in state["attempts"]]
    final = next(a for a in attempts if a.number == state["final_attempt"])
    show_evaluation(final.evaluation, f"Final scorecard - attempt {final.number} of {len(attempts)}")
    out = Path(state["output_dir"])
    console.print(f"Lesson:        {out / 'lesson.md'}\nRejection log: {out / 'rejection_log.md'}")


@app.command()
def evaluate(
    file: Path = typer.Argument(..., exists=True, help="Lesson markdown file to evaluate."),
    topic: str = typer.Option("Introduction to RAG", "--topic", "-t"),
    inject: Optional[str] = typer.Option(None, help=f"Corrupt the file first: comma list of {INJECT_KINDS}."),
    code_only: bool = typer.Option(False, help="Only run deterministic checks (no API key needed)."),
) -> None:
    """Evaluate any lesson file against the rubric (great for the 'catch a deliberate error' demo)."""
    from .evaluator import Evaluator

    s = Settings()
    pack = find_topic_pack(topic, s.data_dir) or TopicPack(topic, topic, [], [], "", grounded=False)
    md = file.read_text(encoding="utf-8")
    kinds = _parse_kinds(inject)
    if kinds is not None:
        md, applied = inject_errors(md, kinds or None)
        console.print(f"[magenta]Injected errors: {', '.join(applied)}[/magenta]")
    judge = None
    if not code_only:
        from .factory import make_judge
        judge = make_judge(s)
    extra = Memory(s.db_path).approved_checks() if s.db_path.exists() else []
    ev = Evaluator(judge, pack, data_dir=s.data_dir, extra_checks=extra, log=log).evaluate(md, code_only=code_only)
    show_evaluation(ev, f"Evaluation of {file.name}")
    raise typer.Exit(code=0 if ev.passed else 1)


@app.command()
def inject(
    file: Path = typer.Argument(..., exists=True),
    out: Path = typer.Option(..., "--out", "-o"),
    kinds: str = typer.Option("factual,jargon,long", help=f"Comma list of {INJECT_KINDS}."),
) -> None:
    """Write a deliberately corrupted copy of a lesson."""
    md, applied = inject_errors(file.read_text(encoding="utf-8"), _parse_kinds(kinds) or None)
    out.write_text(md, encoding="utf-8")
    console.print(f"Wrote {out} with injected errors: {', '.join(applied)}")


@app.command()
def memory() -> None:
    """Show what the system has learned: run history, weakest checks, active rules."""
    m = Memory(Settings().db_path)
    runs = Table(title="Run history (first-attempt quality over time)")
    for c in ["Run", "Status", "Attempts", "1st-attempt failures", "Rules used"]:
        runs.add_column(c)
    rules_by_run = {x["id"]: json.loads(x["rules_used"] or "[]") for x in m.runs(500)}
    for r in m.first_attempt_pass_history():
        runs.add_row(r["id"], r["status"], str(r["attempts"]), str(r["first_attempt_failures"]),
                     str(len(rules_by_run.get(r["id"], []))))
    console.print(runs)
    rates = Table(title="Pass rate per check (all attempts)")
    for c in ["Check", "Name", "Passed/Total", "Pass rate %"]:
        rates.add_column(c)
    for r in m.check_pass_rates():
        rates.add_row(r["check_id"], r["name"] or "", f"{r['passed']}/{r['total']}", str(r["pass_rate"]))
    console.print(rates)
    _print_rules(m)
    pending = m.proposals("pending")
    if pending:
        console.print(f"[yellow]{len(pending)} rubric proposal(s) pending - see `lessonforge rubric list`[/yellow]")


def _print_rules(m: Memory) -> None:
    t = Table(title="Learned rules (added to the writer prompt)")
    for c in ["ID", "Active", "From check", "Applied", "Rule"]:
        t.add_column(c)
    for r in m.all_rules():
        t.add_row(str(r["id"]), "yes" if r["active"] else "no", r["source_check"] or "",
                  str(r["times_applied"]), r["rule"])
    console.print(t)


@rules_app.command("list")
def rules_list() -> None:
    _print_rules(Memory(Settings().db_path))


@rules_app.command("disable")
def rules_disable(rule_id: int) -> None:
    Memory(Settings().db_path).set_rule_active(rule_id, False)
    console.print(f"Rule {rule_id} disabled.")


@rules_app.command("enable")
def rules_enable(rule_id: int) -> None:
    Memory(Settings().db_path).set_rule_active(rule_id, True)
    console.print(f"Rule {rule_id} enabled.")


@app.command()
def feedback(run_id: str, note: str) -> None:
    """Record human reviewer feedback on a run; the next reflection learns from it."""
    fid = Memory(Settings().db_path).add_feedback(run_id, note)
    console.print(f"Feedback #{fid} saved. It will be used at the end of the next run (or `lessonforge reflect`).")


@app.command("reflect")
def reflect_cmd() -> None:
    """Run the reflection step now (learn rules from repeated failures + feedback)."""
    from .factory import make_reflector
    from .reflection import reflect

    s = Settings()
    report = reflect(Memory(s.db_path), make_reflector(s), None, min_runs=s.reflection_min_runs,
                     max_active_rules=s.max_active_rules)
    if report.skipped_reason:
        console.print(f"Skipped: {report.skipped_reason}")
    for r in report.new_rules:
        console.print(f"[green]New rule:[/green] {r}")
    for p in report.new_proposals:
        console.print(f"[yellow]Rubric proposal:[/yellow] {p}")


@rubric_app.command("list")
def rubric_list() -> None:
    t = Table(title="Rubric proposals")
    for c in ["ID", "Status", "Criterion", "Rationale"]:
        t.add_column(c)
    for p in Memory(Settings().db_path).proposals():
        t.add_row(str(p["id"]), p["status"], p["criterion"], p["rationale"] or "")
    console.print(t)


@rubric_app.command("approve")
def rubric_approve(proposal_id: int) -> None:
    Memory(Settings().db_path).set_proposal_status(proposal_id, "approved")
    console.print(f"Proposal {proposal_id} approved: it is now check X{proposal_id} in every evaluation.")


@rubric_app.command("reject")
def rubric_reject(proposal_id: int) -> None:
    Memory(Settings().db_path).set_proposal_status(proposal_id, "rejected")
    console.print(f"Proposal {proposal_id} rejected.")


@app.command()
def graph() -> None:
    """Print the LangGraph workflow as a Mermaid diagram."""
    from .graph import build_graph, Deps

    class _Stub:
        name = "stub"

        def chat(self, *a, **k):  # pragma: no cover
            raise RuntimeError

    console.print(build_graph(Deps(settings=Settings(), writer=_Stub(), judge=_Stub())).get_graph().draw_mermaid())


@app.command()
def show(path: Path = typer.Argument(Path("outputs/latest/lesson.md"), exists=True)) -> None:
    """Render a lesson in the terminal."""
    console.print(Markdown(path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    app()
