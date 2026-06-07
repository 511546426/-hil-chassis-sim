#!/usr/bin/env python3
"""Parse colcon gtest XML under build/<pkg>/test_results and print a summary."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_gtest_xml(path: Path) -> list[dict]:
    rows: list[dict] = []
    root = ET.parse(path).getroot()
    for suite in root.findall(".//testsuite"):
        suite_name = suite.get("name", "?")
        for case in suite.findall("testcase"):
            name = case.get("name", "?")
            time_s = case.get("time", "0")
            failure = case.find("failure")
            error = case.find("error")
            skipped = case.get("status") == "notrun" or case.find("skipped") is not None
            if failure is not None:
                status = "FAIL"
                detail = (failure.text or failure.get("message") or "").strip()
            elif error is not None:
                status = "ERROR"
                detail = (error.text or error.get("message") or "").strip()
            elif skipped:
                status = "SKIP"
                detail = ""
            else:
                status = "PASS"
                detail = ""
            rows.append(
                {
                    "suite": suite_name,
                    "name": name,
                    "status": status,
                    "time_s": time_s,
                    "detail": detail,
                    "file": path.name,
                }
            )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "results_dir",
        type=Path,
        help="e.g. ros2_ws/build/embodied_core/test_results",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Print markdown table (default: plain text)",
    )
    args = parser.parse_args()

    if not args.results_dir.is_dir():
        print(f"错误: 目录不存在 {args.results_dir}", file=sys.stderr)
        return 1

    xml_files = sorted(args.results_dir.rglob("*.gtest.xml"))
    if not xml_files:
        print(f"错误: 未找到 *.gtest.xml under {args.results_dir}", file=sys.stderr)
        return 1

    all_rows: list[dict] = []
    for xf in xml_files:
        all_rows.extend(parse_gtest_xml(xf))

    passed = sum(1 for r in all_rows if r["status"] == "PASS")
    failed = sum(1 for r in all_rows if r["status"] in ("FAIL", "ERROR"))
    skipped = sum(1 for r in all_rows if r["status"] == "SKIP")
    total = len(all_rows)

    if args.markdown:
        print("## embodied_core 单元测试报告\n")
        print(f"**合计**: {passed}/{total} 通过", end="")
        if failed:
            print(f"，{failed} 失败", end="")
        if skipped:
            print(f"，{skipped} 跳过", end="")
        print("\n")
        print("| 套件 | 用例 | 结果 | 耗时(s) |")
        print("|------|------|------|---------|")
        for r in all_rows:
            icon = {"PASS": "✅", "FAIL": "❌", "ERROR": "💥", "SKIP": "⏭"}.get(
                r["status"], "?"
            )
            print(
                f"| {r['suite']} | {r['name']} | {icon} {r['status']} | {r['time_s']} |"
            )
        failures = [r for r in all_rows if r["status"] in ("FAIL", "ERROR")]
        if failures:
            print("\n### 失败详情\n")
            for r in failures:
                print(f"- **{r['suite']}.{r['name']}**")
                if r["detail"]:
                    print(f"  ```\n  {r['detail']}\n  ```")
    else:
        for r in all_rows:
            print(f"{r['status']:5}  {r['suite']}.{r['name']}  ({r['time_s']}s)")
        print(f"\nPASS {passed}/{total}", end="")
        if failed:
            print(f"  FAIL {failed}", end="")
        print()

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
