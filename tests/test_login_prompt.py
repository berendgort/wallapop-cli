import io
import subprocess

from walla.account import prompt


def test_clipboard_cookie_only_takes_cookie_text(monkeypatch):
    monkeypatch.setattr(prompt.shutil, "which", lambda name: name == "wl-paste")
    clip = {"text": "some random clipboard text"}

    def fake_run(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, stdout=clip["text"])

    monkeypatch.setattr(prompt.subprocess, "run", fake_run)
    assert prompt._clipboard_cookie() == ""
    clip["text"] = "eyJabc.def.ghi\n"
    assert prompt._clipboard_cookie() == "eyJabc.def.ghi"


def test_read_hidden_without_tty_reads_full_long_line(monkeypatch):
    long_cookie = "eyJ" + "x" * 6000
    monkeypatch.setattr(prompt.sys, "stdin", io.StringIO(long_cookie + "\n"))
    assert prompt._read_hidden("Cookie: ").strip() == long_cookie
