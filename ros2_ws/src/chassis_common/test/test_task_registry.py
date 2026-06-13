"""Tests for unified task registry (P3-C3-1)."""

from __future__ import annotations

import os
import unittest

from chassis_common.task_registry import (
    get_task_entry,
    gym_spec_dict,
    load_task_registry,
    match_task_entry,
)


class TaskRegistryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
        )
        os.environ.setdefault('CHASSIS_DEMO_ROOT', root)

    def test_load_all_tasks(self) -> None:
        registry = load_task_registry()
        self.assertIn('push_red_box', registry)
        self.assertIn('nav_to_box_red', registry)
        self.assertIn('nav_to_point', registry)

    def test_push_entry_fields(self) -> None:
        entry = get_task_entry('push_red_box')
        self.assertEqual(entry.recommended_brain, 'rule')
        self.assertEqual(entry.monitor.mode, 'push')
        self.assertEqual(entry.planner_goals[0].kind, 'PUSH_RED_BOX')
        gym = gym_spec_dict(entry)
        self.assertEqual(gym['goal']['object_name'], 'box_red')

    def test_match_alias(self) -> None:
        entry = match_task_entry('推红箱')
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.id, 'push_red_box')

    def test_gym_task_spec_by_id(self) -> None:
        from embodied_gym.core.task_spec import load_task_spec_by_id

        spec = load_task_spec_by_id('nav_to_point')
        self.assertEqual(spec.name, 'nav_to_point')
        self.assertEqual(spec.goal.type, 'point')

    def test_planner_templates_from_registry(self) -> None:
        from embodied_planner.templates import load_task_templates, match_template

        templates = load_task_templates()
        self.assertIn('nav_to_box_red', templates)
        tpl = match_template('go to red box')
        self.assertIsNotNone(tpl)
        assert tpl is not None
        self.assertEqual(tpl.id, 'nav_to_box_red')
        self.assertEqual(tpl.recommended_brain, 'rl')

    def test_benchmark_resolve(self) -> None:
        import sys
        from pathlib import Path

        scripts = Path(__file__).resolve().parents[4] / 'scripts'
        sys.path.insert(0, str(scripts))
        from benchmark_lib import resolve_scenario_spec

        spec = resolve_scenario_spec(
            {'name': 'rule_push', 'task_id': 'push_red_box', 'brain': 'rule'}
        )
        self.assertEqual(spec.mode, 'push')
        self.assertEqual(spec.task, 'push_red_box')
        self.assertEqual(spec.max_steps, 1500)


if __name__ == '__main__':
    unittest.main()
