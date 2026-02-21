"""tests/unit/test_json_file_writer_poster.py — write_poster 方法测试"""

import json

from gmp.output.json_file_writer import JSONFileWriter


def test_write_poster(tmp_path):
    writer = JSONFileWriter(str(tmp_path))
    data = {"generated_at": "2026-02-21T08:00:00+08:00", "days": [], "groups": []}
    writer.write_poster(data)
    result = json.loads((tmp_path / "poster.json").read_text(encoding="utf-8"))
    assert result["generated_at"] == "2026-02-21T08:00:00+08:00"
