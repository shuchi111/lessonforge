"""LessonForge viewer: run the loop and inspect attempts, failures, diffs and memory.

Run with:  streamlit run app.py
"""
from __future__ import annotations

import difflib
import json
from pathlib import Path

import streamlit as st

from lessonforge.config import Settings
from lessonforge.inject import ALL as INJECT_KINDS
from lessonforge.memory import Memory

st.set_page_config(page_title="LessonForge", layout="wide")
settings = Settings()


def load_run(run_id: str) -> dict | None:
    path = settings.outputs_dir / run_id / "run.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def checks_table(results: list[dict]) -> list[dict]:
    return [{"Check": f"{r['id']} {r['name']}", "Result": "PASS" if r["passed"] else "FAIL",
             "Method": r["method"], "Dimension": r["dimension"], "Reason": r["reason"],
             "Evidence": r["evidence"], "Fix": r["fix"]} for r in results]


st.title("LessonForge: Self-Evaluating Lesson Generator")
st.caption("generate → evaluate (code checks + LLM judges) → regenerate with feedback → ship or flag for a human")

with st.sidebar:
    st.header("Run the loop")
    topic = st.text_input("Topic", "Introduction to RAG")
    max_retries = st.number_input("Max retries", 0, 3, settings.max_retries)
    inject_on = st.toggle("Demo: inject deliberate errors into attempt 1")
    kinds = st.multiselect("Error kinds", INJECT_KINDS, default=["factual", "jargon", "long"],
                           disabled=not inject_on)
    use_rules = st.toggle("Use learned rules from memory", value=True)
    st.caption(f"Writer: `{settings.writer_model}`  \nJudge: `{settings.judge_model}`")
    if st.button("Generate lesson", type="primary", disabled=not settings.groq_api_key):
        from lessonforge.factory import make_deps
        from lessonforge.graph import new_run_id, run_pipeline

        settings.max_retries = int(max_retries)
        with st.status("Running LessonForge...", expanded=True) as status:
            deps = make_deps(settings, inject=kinds if inject_on else None,
                             use_learned_rules=use_rules, log=lambda m: st.write(m))
            run_id = new_run_id()
            state = run_pipeline(topic, deps, run_id)
            status.update(label=f"Done: {state['status']}", state="complete")
        st.session_state["selected_run"] = run_id
    if not settings.groq_api_key:
        st.warning("Set GROQ_API_KEY in .env to generate.")

memory = Memory(settings.db_path)
runs = [r for r in memory.runs(100) if r["finished_at"]]
if not runs:
    st.info("No runs yet. Generate a lesson from the sidebar, or run `lessonforge run` in a terminal.")
    st.stop()

labels = {r["id"]: f"{r['id']} · {r['status']} · {r['attempts']} attempt(s)"
          + (" · injected errors" if r["injected_errors"] not in (None, "[]") else "") for r in runs}
ids = list(labels)
default = ids.index(st.session_state["selected_run"]) if st.session_state.get("selected_run") in ids else 0
run_id = st.selectbox("Run", ids, index=default, format_func=labels.get)
run = load_run(run_id)
if run is None:
    st.error(f"outputs/{run_id}/run.json not found.")
    st.stop()

attempts = run["attempts"]
final = next(a for a in attempts if a["number"] == run["final_attempt"])
cols = st.columns(4)
cols[0].metric("Status", "PASSED" if run["status"] == "passed" else "NEEDS REVIEW")
cols[1].metric("Attempts", len(attempts))
cols[2].metric("Checks passed (final)",
               f"{sum(r['passed'] for r in final['evaluation']['results'])}/{len(final['evaluation']['results'])}")
cols[3].metric("Learned rules used", len(run.get("rules", [])))

tab_lesson, tab_attempts, tab_diff, tab_log, tab_memory = st.tabs(
    ["Final lesson", "Attempts & checks", "What changed", "Rejection log", "Memory & learning"])

with tab_lesson:
    st.markdown(final["lesson_md"])

with tab_attempts:
    for a in attempts:
        res = a["evaluation"]["results"]
        failed = [r for r in res if not r["passed"]]
        title = f"Attempt {a['number']}: {'PASS' if not failed else 'FAIL - ' + ', '.join(r['id'] for r in failed)}"
        with st.expander(title, expanded=bool(failed)):
            if a.get("injected_errors"):
                st.warning(f"Deliberately injected errors: {', '.join(a['injected_errors'])}")
            if a.get("changes"):
                st.markdown("**Writer's change log for this attempt:**")
                st.markdown(a["changes"])
            st.dataframe(checks_table(res), hide_index=True, width="stretch")
            with st.popover("Show lesson text"):
                st.markdown(a["lesson_md"])

with tab_diff:
    if len(attempts) < 2:
        st.info("This run passed on the first attempt, so there is nothing to compare.")
    else:
        nums = [a["number"] for a in attempts]
        c1, c2 = st.columns(2)
        left = c1.selectbox("From attempt", nums, index=0)
        right = c2.selectbox("To attempt", nums, index=len(nums) - 1)
        a_md = next(a for a in attempts if a["number"] == left)["lesson_md"].splitlines()
        b_md = next(a for a in attempts if a["number"] == right)["lesson_md"].splitlines()
        diff = "\n".join(difflib.unified_diff(a_md, b_md, f"attempt {left}", f"attempt {right}", lineterm=""))
        st.code(diff or "No differences.", language="diff")

with tab_log:
    log_path = settings.outputs_dir / run_id / "rejection_log.md"
    st.markdown(log_path.read_text(encoding="utf-8") if log_path.exists() else "No rejection log found.")

with tab_memory:
    st.subheader("First-attempt quality over runs")
    history = memory.first_attempt_pass_history()
    if history:
        st.line_chart({"First-attempt failed checks": [h["first_attempt_failures"] for h in history]})
        st.caption("Lower is better: learned rules should reduce failures on the first attempt.")
    st.subheader("Learned rules (added to the writer prompt)")
    st.dataframe(memory.all_rules(), hide_index=True, width="stretch")
    st.subheader("Pass rate per check")
    st.dataframe(memory.check_pass_rates(), hide_index=True, width="stretch")
    st.subheader("Rubric proposals (need human approval)")
    proposals = memory.proposals()
    if not proposals:
        st.caption("None yet. Add feedback with `lessonforge feedback <run_id> \"...\"`.")
    for p in proposals:
        c1, c2, c3 = st.columns([6, 1, 1])
        c1.write(f"**#{p['id']}** [{p['status']}] {p['criterion']}  \n_{p['rationale']}_")
        if p["status"] == "pending":
            if c2.button("Approve", key=f"ap{p['id']}"):
                memory.set_proposal_status(p["id"], "approved")
                st.rerun()
            if c3.button("Reject", key=f"rj{p['id']}"):
                memory.set_proposal_status(p["id"], "rejected")
                st.rerun()
    st.subheader("Give feedback on this run")
    note = st.text_area("What should be better? (the next reflection learns from this)")
    if st.button("Save feedback") and note.strip():
        memory.add_feedback(run_id, note.strip())
        st.success("Saved. It will be used at the end of the next run.")
