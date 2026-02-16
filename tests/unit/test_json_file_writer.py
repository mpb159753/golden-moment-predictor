"""tests/unit/test_json_file_writer.py — JSONFileWriter 单元测试"""

import json
from pathlib import Path

import pytest

from gmp.output.json_file_writer import JSONFileWriter


# ── fixtures ──────────────────────────────────────────────


@pytest.fixture
def writer(tmp_path: Path) -> JSONFileWriter:
    """创建带临时目录的 writer"""
    output_dir = tmp_path / "public" / "data"
    archive_dir = tmp_path / "archive"
    return JSONFileWriter(
        output_dir=str(output_dir),
        archive_dir=str(archive_dir),
    )


@pytest.fixture
def sample_forecast() -> dict:
    return {
        "viewpoint_id": "vp001",
        "viewpoint_name": "牛背山",
        "generated_at": "2026-02-14T00:00:00Z",
        "forecast_days": 3,
        "daily": [],
    }


@pytest.fixture
def sample_timeline() -> dict:
    return {
        "viewpoint_id": "vp001",
        "viewpoint_name": "牛背山",
        "generated_at": "2026-02-14T00:00:00Z",
        "days": [],
    }


# ── write_viewpoint ──────────────────────────────────────


class TestWriteViewpoint:
    def test_creates_forecast_json(
        self, writer: JSONFileWriter, sample_forecast: dict, sample_timeline: dict,
    ):
        """写入 viewpoint 后应在 viewpoints/{id}/ 下创建 forecast.json"""
        writer.write_viewpoint("vp001", sample_forecast, sample_timeline)

        path = Path(writer._output_dir) / "viewpoints" / "vp001" / "forecast.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["viewpoint_id"] == "vp001"

    def test_creates_timeline_json(
        self, writer: JSONFileWriter, sample_forecast: dict, sample_timeline: dict,
    ):
        """写入 viewpoint 后应在 viewpoints/{id}/ 下创建 timeline.json"""
        writer.write_viewpoint("vp001", sample_forecast, sample_timeline)

        path = Path(writer._output_dir) / "viewpoints" / "vp001" / "timeline.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["viewpoint_id"] == "vp001"

    def test_auto_creates_subdirectories(
        self, writer: JSONFileWriter, sample_forecast: dict, sample_timeline: dict,
    ):
        """子目录应自动创建"""
        vp_dir = Path(writer._output_dir) / "viewpoints" / "vp001"
        assert not vp_dir.exists()

        writer.write_viewpoint("vp001", sample_forecast, sample_timeline)
        assert vp_dir.is_dir()

    def test_json_is_utf8_with_indent(
        self, writer: JSONFileWriter, sample_forecast: dict, sample_timeline: dict,
    ):
        """JSON 文件应为 UTF-8 编码且格式化（缩进）"""
        writer.write_viewpoint("vp001", sample_forecast, sample_timeline)

        path = Path(writer._output_dir) / "viewpoints" / "vp001" / "forecast.json"
        text = path.read_text(encoding="utf-8")
        # 缩进文件的行数应 > 1
        assert len(text.strip().splitlines()) > 1
        # 中文应正常显示（不被转义）
        assert "牛背山" in text


# ── write_route ──────────────────────────────────────────


class TestWriteRoute:
    def test_creates_route_forecast_json(self, writer: JSONFileWriter):
        """写入 route 后应在 routes/{id}/ 下创建 forecast.json"""
        route_data = {"route_id": "rt001", "route_name": "经典环线"}
        writer.write_route("rt001", route_data)

        path = Path(writer._output_dir) / "routes" / "rt001" / "forecast.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["route_id"] == "rt001"


# ── write_index ──────────────────────────────────────────


class TestWriteIndex:
    def test_creates_index_json(self, writer: JSONFileWriter):
        """应在 output_dir 根目录创建 index.json"""
        viewpoints = [{"id": "vp001", "name": "牛背山"}]
        routes = [{"id": "rt001", "name": "经典环线"}]
        writer.write_index(viewpoints, routes)

        path = Path(writer._output_dir) / "index.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["viewpoints"] == viewpoints
        assert data["routes"] == routes


# ── write_meta ──────────────────────────────────────────


class TestWriteMeta:
    def test_creates_meta_json(self, writer: JSONFileWriter):
        """应在 output_dir 根目录创建 meta.json"""
        metadata = {"generated_at": "2026-02-14T00:00:00Z", "engine_version": "1.0.0"}
        writer.write_meta(metadata)

        path = Path(writer._output_dir) / "meta.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["generated_at"] == "2026-02-14T00:00:00Z"
        assert data["engine_version"] == "1.0.0"


# ── archive ──────────────────────────────────────────────


class TestArchive:
    def test_copies_output_to_archive(
        self,
        writer: JSONFileWriter,
        sample_forecast: dict,
        sample_timeline: dict,
    ):
        """archive 应将 output_dir 全部内容复制到 archive_dir/timestamp/"""
        writer.write_viewpoint("vp001", sample_forecast, sample_timeline)
        writer.write_meta({"generated_at": "2026-02-14T00:00:00Z", "engine_version": "1.0.0"})

        writer.archive("2026-02-14T00-00")

        archive_root = Path(writer._archive_dir) / "2026-02-14T00-00"
        assert archive_root.is_dir()

        # 检查关键文件存在
        assert (archive_root / "viewpoints" / "vp001" / "forecast.json").exists()
        assert (archive_root / "viewpoints" / "vp001" / "timeline.json").exists()
        assert (archive_root / "meta.json").exists()

    def test_archive_preserves_content(
        self,
        writer: JSONFileWriter,
        sample_forecast: dict,
        sample_timeline: dict,
    ):
        """archive 内容应与原始内容一致"""
        writer.write_viewpoint("vp001", sample_forecast, sample_timeline)
        writer.archive("2026-02-14T00-00")

        original = Path(writer._output_dir) / "viewpoints" / "vp001" / "forecast.json"
        archived = (
            Path(writer._archive_dir)
            / "2026-02-14T00-00"
            / "viewpoints"
            / "vp001"
            / "forecast.json"
        )
        assert original.read_text() == archived.read_text()
