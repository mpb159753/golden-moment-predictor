# MH1B: 海报数据生成器 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 新建 `poster_generator.py`，读取已生成的 forecast+timeline JSON 文件，按山系分组聚合为 `poster.json`，集成到 `generate-all` 命令中。

**Architecture:** `PosterGenerator` 读取已生成的 `viewpoints/{id}/forecast.json` 和 `timeline_{date}.json`，按 viewpoint 的 `groups` 字段分组、提取上午/下午天气+最佳事件，输出聚合后的 `poster.json`。

**Tech Stack:** Python 3.11

**设计文档:** [12-poster-page.md](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/12-poster-page.md) §12.5

**依赖:** MH1A（Viewpoint `groups` 字段必须已添加）

**后续计划:** MH1C（海报前端页面）

---

## Proposed Changes

### Task 1: PosterGenerator 核心模块

---

#### [NEW] [poster_generator.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/gmp/output/poster_generator.py)

```python
"""gmp/output/poster_generator.py — 海报数据聚合器

读取已生成的 forecast+timeline JSON，按山系分组聚合为 poster.json。
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gmp.core.config_loader import ViewpointConfig

_CST = timezone(timedelta(hours=8))

# 山系分组元数据 (key → 中文名 + 排序序号)
GROUP_META: dict[str, dict] = {
    "gongga": {"name": "贡嘎山系", "order": 1},
    "siguniang": {"name": "四姑娘山", "order": 2},
    "yala": {"name": "雅拉山系", "order": 3},
    "genie": {"name": "格聂山系", "order": 4},
    "yading": {"name": "亚丁景区", "order": 5},
    "318": {"name": "318 沿途", "order": 6},
    "lixiao": {"name": "理小路沿途", "order": 7},
    "other": {"name": "其它景区", "order": 8},
}

# WMO 天气代码 → 中文映射
WMO_WEATHER_MAP: dict[int, str] = {
    0: "晴天", 1: "晴天",
    2: "多云", 3: "阴天",
    45: "雾", 48: "雾",
    51: "小雨", 53: "小雨", 55: "小雨",
    61: "中雨", 63: "中雨",
    65: "大雨", 67: "大雨",
    71: "小雪", 73: "小雪",
    75: "大雪", 77: "大雪",
}

# 上午/下午事件归属
AM_EVENTS = {"sunrise_golden_mountain", "frost", "snow_tree", "ice_icicle"}
PM_EVENTS = {"sunset_golden_mountain", "cloud_sea", "stargazing"}


class PosterGenerator:
    """海报数据聚合器"""

    def __init__(self, output_dir: str = "public/data") -> None:
        self._output_dir = Path(output_dir)

    def generate(
        self,
        viewpoint_config: ViewpointConfig,
        days: int = 5,
    ) -> dict:
        """聚合所有景点数据生成 poster.json 格式的 dict"""
        now = datetime.now(_CST)
        date_list = [
            (now + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(days)
        ]

        # 按 groups 分组 viewpoint (一个景点可属于多个组)
        groups_map: dict[str, list] = {}
        for vp in viewpoint_config.list_all():
            vp_groups = vp.groups if vp.groups else ["other"]
            for group_key in vp_groups:
                if group_key not in groups_map:
                    groups_map[group_key] = []
                groups_map[group_key].append(vp)

        # 构建每组数据
        groups = []
        for group_key, meta in sorted(
            GROUP_META.items(), key=lambda x: x[1]["order"]
        ):
            vps = groups_map.get(group_key, [])
            if not vps:
                continue

            viewpoints_data = []
            for vp in vps:
                daily = self._build_daily(vp.id, date_list)
                viewpoints_data.append({
                    "id": vp.id,
                    "name": vp.name,
                    "daily": daily,
                })

            groups.append({
                "name": meta["name"],
                "key": group_key,
                "viewpoints": viewpoints_data,
            })

        return {
            "generated_at": now.isoformat(),
            "days": date_list,
            "groups": groups,
        }

    def _build_daily(
        self, viewpoint_id: str, dates: list[str]
    ) -> list[dict]:
        """为单个景点构建多日 AM/PM 数据"""
        forecast = self._load_forecast(viewpoint_id)
        result = []
        for date_str in dates:
            timeline = self._load_timeline(viewpoint_id, date_str)
            am = self._extract_half_day(
                forecast, timeline, date_str, "am"
            )
            pm = self._extract_half_day(
                forecast, timeline, date_str, "pm"
            )
            result.append({"date": date_str, "am": am, "pm": pm})
        return result

    def _load_forecast(self, viewpoint_id: str) -> dict:
        """加载 viewpoint 的 forecast.json"""
        path = (
            self._output_dir / "viewpoints" / viewpoint_id / "forecast.json"
        )
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_timeline(self, viewpoint_id: str, date_str: str) -> dict:
        """加载 viewpoint 的 timeline_{date}.json"""
        path = (
            self._output_dir
            / "viewpoints"
            / viewpoint_id
            / f"timeline_{date_str}.json"
        )
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _extract_half_day(
        self,
        forecast: dict,
        timeline: dict,
        date_str: str,
        half: str,  # "am" or "pm"
    ) -> dict:
        """提取上午/下午的天气+最佳事件"""
        weather = self._get_dominant_weather(timeline, half)

        event_name = ""
        score = 0
        target_events = AM_EVENTS if half == "am" else PM_EVENTS

        for day_data in forecast.get("daily", []):
            if day_data.get("date") != date_str:
                continue
            best_score = 0
            for ev in day_data.get("events", []):
                ev_type = ev.get("event_type", "")
                ev_score = ev.get("score", 0)
                if ev_score >= 50 and ev_type in target_events:
                    if ev_score > best_score:
                        best_score = ev_score
                        event_name = ev.get("display_name", ev_type)
                        score = ev_score
            # 如果无专属时段事件 >= 50, 检查 clear_sky
            if not event_name:
                for ev in day_data.get("events", []):
                    if (
                        ev.get("event_type") == "clear_sky"
                        and ev.get("score", 0) >= 50
                    ):
                        score = ev["score"]
            break

        return {"weather": weather, "event": event_name, "score": score}

    def _get_dominant_weather(self, timeline: dict, half: str) -> str:
        """从 timeline 中提取上午/下午的主导天气"""
        hours_range = range(6, 12) if half == "am" else range(12, 18)
        weather_codes: list[int] = []

        for entry in timeline.get("hourly", []):
            if entry.get("hour") in hours_range:
                weather = entry.get("weather", {})
                code = weather.get("weather_code")
                if code is not None:
                    weather_codes.append(code)

        if not weather_codes:
            return "未知"

        most_common = Counter(weather_codes).most_common(1)[0][0]
        return WMO_WEATHER_MAP.get(most_common, "未知")
```

**Step 1:** 创建文件

**Step 2:** Commit

```bash
git add gmp/output/poster_generator.py
git commit -m "feat(poster): add PosterGenerator core module"
```

---

### Task 2: JSONFileWriter 新增 write_poster

---

#### [MODIFY] [json_file_writer.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/gmp/output/json_file_writer.py)

在 `write_meta()` 之后新增：

```diff
+    def write_poster(self, data: dict) -> None:
+        """写入 poster.json"""
+        output = Path(self._output_dir)
+        output.mkdir(parents=True, exist_ok=True)
+        self._write_json(output / "poster.json", data)
```

**Step 1:** 修改代码

**Step 2:** Commit

```bash
git add gmp/output/json_file_writer.py
git commit -m "feat(output): add write_poster to JSONFileWriter"
```

---

### Task 3: BatchGenerator 集成

---

#### [MODIFY] [batch_generator.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/gmp/core/batch_generator.py)

在 `generate_all()` 方法的步骤 4 (meta.json) 之后新增步骤 5：

```diff
         # 4. 生成 meta.json
         ...

+        # 5. 生成 poster.json
+        from gmp.output.poster_generator import PosterGenerator
+        poster_gen = PosterGenerator(self._output_dir)
+        poster_data = poster_gen.generate(self._viewpoint_config, days=min(days, 5))
+        self._json_writer.write_poster(poster_data)

         # 5. 归档  (原编号改为 6)
```

**Step 1:** 修改代码

**Step 2:** Run tests

Run: `cd /Users/mpb/WorkSpace/golden-moment-predictor && python -m pytest tests/unit/test_batch_generator.py -v`

**Step 3:** Commit

```bash
git add gmp/core/batch_generator.py
git commit -m "feat(batch): integrate poster.json generation into generate-all"
```

---

### Task 4: 单元测试

---

#### [NEW] [test_poster_generator.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/tests/unit/test_poster_generator.py)

```python
import json
import pytest
from unittest.mock import MagicMock
from gmp.output.poster_generator import (
    PosterGenerator,
    WMO_WEATHER_MAP,
    GROUP_META,
)


@pytest.fixture
def tmp_data_dir(tmp_path):
    """创建临时数据目录并写入测试数据"""
    vp_dir = tmp_path / "viewpoints" / "niubei_gongga"
    vp_dir.mkdir(parents=True)

    forecast = {
        "daily": [{
            "date": "2026-02-21",
            "events": [
                {"event_type": "sunrise_golden_mountain", "display_name": "日照金山", "score": 90},
                {"event_type": "cloud_sea", "display_name": "云海", "score": 75},
                {"event_type": "clear_sky", "display_name": "晴天", "score": 80},
            ],
        }],
    }
    (vp_dir / "forecast.json").write_text(
        json.dumps(forecast, ensure_ascii=False), encoding="utf-8"
    )

    timeline = {
        "hourly": [{"hour": h, "weather": {"weather_code": 0}} for h in range(24)],
    }
    (vp_dir / "timeline_2026-02-21.json").write_text(
        json.dumps(timeline), encoding="utf-8"
    )
    return tmp_path


@pytest.fixture
def mock_viewpoint_config():
    vp = MagicMock()
    vp.id = "niubei_gongga"
    vp.name = "牛背山"
    vp.groups = ["gongga"]
    config = MagicMock()
    config.list_all.return_value = [vp]
    return config


def test_generate_basic_structure(tmp_data_dir, mock_viewpoint_config):
    gen = PosterGenerator(str(tmp_data_dir))
    result = gen.generate(mock_viewpoint_config, days=1)
    assert "generated_at" in result
    assert "days" in result
    assert "groups" in result
    assert len(result["groups"]) >= 1


def test_am_event_extraction(tmp_data_dir, mock_viewpoint_config):
    gen = PosterGenerator(str(tmp_data_dir))
    result = gen.generate(mock_viewpoint_config, days=1)
    am = result["groups"][0]["viewpoints"][0]["daily"][0]["am"]
    assert am["event"] == "日照金山"
    assert am["score"] == 90


def test_pm_event_extraction(tmp_data_dir, mock_viewpoint_config):
    gen = PosterGenerator(str(tmp_data_dir))
    result = gen.generate(mock_viewpoint_config, days=1)
    pm = result["groups"][0]["viewpoints"][0]["daily"][0]["pm"]
    assert pm["event"] == "云海"
    assert pm["score"] == 75


def test_weather_mapping():
    assert WMO_WEATHER_MAP[0] == "晴天"
    assert WMO_WEATHER_MAP[3] == "阴天"
    assert WMO_WEATHER_MAP[71] == "小雪"


def test_missing_data_graceful(tmp_path):
    vp = MagicMock()
    vp.id = "nonexistent"
    vp.name = "不存在"
    vp.groups = ["other"]
    config = MagicMock()
    config.list_all.return_value = [vp]
    gen = PosterGenerator(str(tmp_path))
    result = gen.generate(config, days=1)
    assert len(result["groups"]) >= 1


def test_multi_group_viewpoint(tmp_data_dir):
    vp = MagicMock()
    vp.id = "niubei_gongga"
    vp.name = "牛背山"
    vp.groups = ["gongga", "318"]
    config = MagicMock()
    config.list_all.return_value = [vp]
    gen = PosterGenerator(str(tmp_data_dir))
    result = gen.generate(config, days=1)
    group_keys = [g["key"] for g in result["groups"]]
    assert "gongga" in group_keys
    assert "318" in group_keys
```

**Step 1:** 写测试（先跑失败）

Run: `cd /Users/mpb/WorkSpace/golden-moment-predictor && python -m pytest tests/unit/test_poster_generator.py -v`

Expected: FAIL

**Step 2:** 运行通过后提交

Run: `cd /Users/mpb/WorkSpace/golden-moment-predictor && python -m pytest tests/unit/test_poster_generator.py -v`

Expected: All PASS

**Step 3:** Commit

```bash
git add tests/unit/test_poster_generator.py
git commit -m "test(poster): add PosterGenerator unit tests"
```

---

#### [NEW] [test_json_file_writer_poster.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/tests/unit/test_json_file_writer_poster.py)

```python
import json
from gmp.output.json_file_writer import JSONFileWriter


def test_write_poster(tmp_path):
    writer = JSONFileWriter(str(tmp_path))
    data = {"generated_at": "2026-02-21T08:00:00+08:00", "days": [], "groups": []}
    writer.write_poster(data)
    result = json.loads((tmp_path / "poster.json").read_text(encoding="utf-8"))
    assert result["generated_at"] == "2026-02-21T08:00:00+08:00"
```

Run: `cd /Users/mpb/WorkSpace/golden-moment-predictor && python -m pytest tests/unit/test_json_file_writer_poster.py -v`

---

## Verification Plan

### Automated Tests

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor
python -m pytest tests/unit/test_poster_generator.py tests/unit/test_json_file_writer_poster.py tests/unit/test_batch_generator.py -v
```

### 集成验证

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor
python -m gmp.main generate-all --days 5 --no-archive
cat public/data/poster.json | python -m json.tool | head -50
```

验证 `poster.json` 包含正确的分组结构。

---

*计划版本: v1.0 | 创建: 2026-02-21 | 拆分自 MH1-poster-page.md v2.0*
