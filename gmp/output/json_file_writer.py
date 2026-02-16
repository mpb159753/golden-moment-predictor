"""gmp/output/json_file_writer.py — JSON 文件写入器

管理输出目录结构、文件写入和历史归档。
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path


class JSONFileWriter:
    """JSON 文件写入与归档管理器"""

    def __init__(
        self,
        output_dir: str = "public/data",
        archive_dir: str = "archive",
    ) -> None:
        self._output_dir = output_dir
        self._archive_dir = archive_dir

    def write_viewpoint(
        self,
        viewpoint_id: str,
        forecast: dict,
        timeline: dict,
    ) -> None:
        """写入 viewpoints/{id}/forecast.json 和 timeline.json"""
        vp_dir = Path(self._output_dir) / "viewpoints" / viewpoint_id
        vp_dir.mkdir(parents=True, exist_ok=True)

        self._write_json(vp_dir / "forecast.json", forecast)
        self._write_json(vp_dir / "timeline.json", timeline)

    def write_route(self, route_id: str, forecast: dict) -> None:
        """写入 routes/{id}/forecast.json"""
        route_dir = Path(self._output_dir) / "routes" / route_id
        route_dir.mkdir(parents=True, exist_ok=True)

        self._write_json(route_dir / "forecast.json", forecast)

    def write_index(self, viewpoints: list, routes: list) -> None:
        """写入 index.json"""
        output = Path(self._output_dir)
        output.mkdir(parents=True, exist_ok=True)

        data = {"viewpoints": viewpoints, "routes": routes}
        self._write_json(output / "index.json", data)

    def write_meta(self, metadata: dict) -> None:
        """写入 meta.json"""
        output = Path(self._output_dir)
        output.mkdir(parents=True, exist_ok=True)

        self._write_json(output / "meta.json", metadata)

    def archive(self, timestamp: str) -> None:
        """将当前 output_dir 内容复制到 archive_dir/timestamp/"""
        src = Path(self._output_dir)
        dst = Path(self._archive_dir) / timestamp

        if src.exists():
            shutil.copytree(src, dst)

    @staticmethod
    def _write_json(path: Path, data: dict) -> None:
        """写入 JSON 文件（UTF-8, 缩进 2 空格, 中文不转义）"""
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
