from pathlib import Path

import webview
from webview.util import parse_file_type

from backend.app.project_files import ensure_project_suffix, read_project_text, write_project_text
from backend.desktop import DesktopProjectApi, PROJECT_FILE_TYPES


class FakeWindow:
    def __init__(self, selections: list[tuple[str, ...] | None]):
        self.selections = selections
        self.calls = 0

    def create_file_dialog(self, *args, **kwargs):
        self.calls += 1
        return self.selections.pop(0)


def test_project_file_suffix_and_atomic_utf8_write(tmp_path: Path):
    assert all(parse_file_type(file_type) for file_type in PROJECT_FILE_TYPES)
    assert ensure_project_suffix(tmp_path / "lesson").name == "lesson.slab.json"
    assert ensure_project_suffix(tmp_path / "lesson.json").name == "lesson.json"
    target = tmp_path / "Mô phỏng.slab.json"
    written = write_project_text(target, '{"name":"Mô phỏng"}')
    assert written == target
    assert read_project_text(written) == '{"name":"Mô phỏng"}'
    assert not list(tmp_path.glob("*.tmp"))


def test_desktop_save_reuses_current_file_and_open_associates_it(tmp_path: Path, monkeypatch):
    first_target = tmp_path / "first lesson"
    opened_target = write_project_text(tmp_path / "opened.json", '{"graph":{"nodes":[],"edges":[]}}')
    fake = FakeWindow([(str(first_target),), (str(opened_target),)])
    monkeypatch.setattr(webview, "windows", [fake])
    api = DesktopProjectApi()

    first = api.save_project('{"version":1}', suggested_name="first lesson.slab.json")
    assert Path(first["path"]).name == "first lesson.slab.json"
    assert read_project_text(Path(first["path"])) == '{"version":1}'
    assert fake.calls == 1

    second = api.save_project('{"version":2}')
    assert second["path"] == first["path"]
    assert read_project_text(Path(first["path"])) == '{"version":2}'
    assert fake.calls == 1

    opened = api.open_project()
    assert opened["content"] == '{"graph":{"nodes":[],"edges":[]}}'
    assert opened["name"] == "opened.json"
    assert fake.calls == 2
