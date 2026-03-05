"""
测试执行脚本

运行所有方案A扩展功能的测试用例并生成报告
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime


def run_tests(test_dir: Path) -> dict:
    """运行测试并返回结果"""
    result = {
        "test_file": test_dir.name,
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "total": 0,
        "duration": 0,
        "success": False,
    }

    try:
        cmd = [sys.executable, "-m", "pytest", str(test_dir), "-v", "--tb=short", "--no-header"]

        start_time = datetime.now()
        process = subprocess.run(
            cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )
        end_time = datetime.now()

        result["duration"] = (end_time - start_time).total_seconds()
        result["output"] = process.stdout
        result["error_output"] = process.stderr

        if process.returncode == 0:
            result["success"] = True

        output = process.stdout + process.stderr

        for line in output.split("\n"):
            if " passed" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed":
                        result["passed"] = int(parts[i - 1])
                    elif part == "failed":
                        result["failed"] = int(parts[i - 1])
                    elif part == "errors":
                        result["errors"] = int(parts[i - 1])
                    elif part == "skipped":
                        result["skipped"] = int(parts[i - 1])

        result["total"] = result["passed"] + result["failed"] + result["errors"] + result["skipped"]

    except Exception as e:
        result["error"] = str(e)
        result["success"] = False

    return result


def generate_report(results: list) -> str:
    """生成测试报告"""
    report = []
    report.append("=" * 80)
    report.append("方案A扩展功能测试报告")
    report.append("=" * 80)
    report.append(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")

    total_passed = 0
    total_failed = 0
    total_errors = 0
    total_skipped = 0
    total_tests = 0
    total_duration = 0

    for result in results:
        report.append("-" * 80)
        report.append(f"测试文件: {result['test_file']}")
        report.append(f"状态: {'[PASS] 通过' if result['success'] else '[FAIL] 失败'}")
        report.append(
            f"总计: {result['total']} | 通过: {result['passed']} | 失败: {result['failed']} | 错误: {result['errors']} | 跳过: {result['skipped']}"
        )
        report.append(f"耗时: {result['duration']:.2f}s")

        if not result["success"] and "error_output" in result:
            report.append("")
            report.append("错误输出:")
            report.append(result["error_output"][:500])

        report.append("")

        total_passed += result["passed"]
        total_failed += result["failed"]
        total_errors += result["errors"]
        total_skipped += result["skipped"]
        total_tests += result["total"]
        total_duration += result["duration"]

    report.append("=" * 80)
    report.append("汇总统计")
    report.append("=" * 80)
    report.append(f"总计测试: {total_tests}")
    report.append(f"通过: {total_passed} ({total_passed / total_tests * 100:.1f}%)")
    report.append(f"失败: {total_failed} ({total_failed / total_tests * 100:.1f}%)")
    report.append(f"错误: {total_errors} ({total_errors / total_tests * 100:.1f}%)")
    report.append(f"跳过: {total_skipped} ({total_skipped / total_tests * 100:.1f}%)")
    report.append(f"总耗时: {total_duration:.2f}s")
    report.append("")

    overall_success = total_failed == 0 and total_errors == 0
    report.append(f"总体状态: {'[PASS] 全部通过' if overall_success else '[FAIL] 存在失败'}")
    report.append("=" * 80)

    return "\n".join(report)


def main():
    """主函数"""
    test_dir = Path(__file__).parent

    test_files = [
        "test_config_base.py",
        "test_error_classifier.py",
        "test_retry_extension.py",
        "test_server_base.py",
    ]

    results = []

    print("开始运行方案A扩展功能测试...")
    print("")

    for test_file in test_files:
        test_path = test_dir / test_file
        if test_path.exists():
            print(f"运行 {test_file}...")
            result = run_tests(test_path)
            results.append(result)
        else:
            print(f"警告: 测试文件 {test_file} 不存在")

    report = generate_report(results)
    print("")
    print(report)

    report_file = test_dir / "test_report.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"")
    print(f"测试报告已保存到: {report_file}")

    overall_success = all(r["success"] for r in results)
    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main())
