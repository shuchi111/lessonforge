"""Smoke test: the Streamlit viewer renders a real (offline) run without errors."""
from __future__ import annotations

from pathlib import Path

from conftest import all_pass_judge
from test_loop import writer_that

from lessonforge.config import Settings
from lessonforge.graph import Deps, run_pipeline
from lessonforge.memory import Memory

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def test_viewer_renders_run(tmp_path, monkeypatch, good_lesson):
    monkeypatch.setenv("LESSONFORGE_DB_PATH", str(tmp_path / "mem.db"))
    monkeypatch.setenv("LESSONFORGE_OUTPUTS_DIR", str(tmp_path / "out"))
    s = Settings()
    run_pipeline("Introduction to RAG", Deps(settings=s, writer=writer_that(good_lesson, good_lesson),
                                             judge=all_pass_judge(), memory=Memory(s.db_path),
                                             inject=["long"]), "run-ui")

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception, at.exception
    assert any("PASSED" == m.value for m in at.metric)
    assert len(at.tabs) == 5
