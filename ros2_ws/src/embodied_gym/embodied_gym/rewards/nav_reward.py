"""导航任务奖励 — 与 TaskSpec.reward 字段对齐。"""

from __future__ import annotations

from dataclasses import dataclass

from embodied_gym.core.task_spec import RewardSpec


@dataclass
class NavRewardBreakdown:
    progress: float = 0.0
    time: float = 0.0
    success: float = 0.0
    out_of_bounds: float = 0.0
    total: float = 0.0


class NavRewardEngine:
    def __init__(self, spec: RewardSpec) -> None:
        self.spec = spec

    def step_reward(
        self,
        *,
        prev_dist: float,
        curr_dist: float,
        success: bool,
        out_of_bounds: bool,
    ) -> NavRewardBreakdown:
        breakdown = NavRewardBreakdown()
        breakdown.progress = self.spec.progress * (prev_dist - curr_dist)
        breakdown.time = self.spec.time
        if success:
            breakdown.success = self.spec.success
        if out_of_bounds:
            breakdown.out_of_bounds = self.spec.out_of_bounds
        breakdown.total = (
            breakdown.progress
            + breakdown.time
            + breakdown.success
            + breakdown.out_of_bounds
        )
        return breakdown
