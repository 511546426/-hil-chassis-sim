"""Tests for LLM mock planner."""

from __future__ import annotations

import os
import unittest

from embodied_planner.llm_mock_planner import LlmMockPlanner
from embodied_planner.llm_schema import LlmTaskClassification


class LlmMockPlannerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
        )
        os.environ.setdefault('CHASSIS_DEMO_ROOT', root)

    def test_paraphrase_push(self) -> None:
        planner = LlmMockPlanner()
        plan = planner.plan('帮我把红箱子推远一点')
        self.assertEqual(plan.source, 'llm_mock')
        self.assertEqual(plan.goals[0].kind, 2)

    def test_nav_paraphrase(self) -> None:
        planner = LlmMockPlanner()
        plan = planner.plan('please go to the red box')
        self.assertEqual(plan.source, 'llm_mock')
        self.assertEqual(plan.goals[0].kind, 1)
        self.assertEqual(plan.goals[0].object_name, 'box_red')

    def test_unknown_rejected(self) -> None:
        planner = LlmMockPlanner()
        with self.assertRaises(ValueError):
            planner.plan('dance like a robot')


class LlmSchemaTest(unittest.TestCase):
    def test_validates_whitelist(self) -> None:
        c = LlmTaskClassification(task_id='push_red_box', confidence=0.9)
        self.assertEqual(c.validated_task_id(min_confidence=0.5), 'push_red_box')

    def test_rejects_unknown(self) -> None:
        c = LlmTaskClassification(task_id='unknown', confidence=0.0)
        with self.assertRaises(ValueError):
            c.validated_task_id(min_confidence=0.5)


if __name__ == '__main__':
    unittest.main()
