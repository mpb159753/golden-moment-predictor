"""共享 test fixtures — 各模块实现时逐步扩充。"""

from gmp.core.models import ScoreResult
from gmp.scoring.models import DataContext, DataRequirement


class StubPlugin:
    """测试用最小 Plugin 实现，满足 ScorerPlugin Protocol"""

    def __init__(
        self,
        event_type: str,
        display_name: str = "Stub",
        requirement: DataRequirement | None = None,
    ):
        self._event_type = event_type
        self._display_name = display_name
        self._requirement = requirement or DataRequirement()

    @property
    def event_type(self) -> str:
        return self._event_type

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def data_requirement(self) -> DataRequirement:
        return self._requirement

    def score(self, context: DataContext) -> ScoreResult | None:
        return None

    def dimensions(self) -> list[str]:
        return []
