"""
P6 反退化测试：仓库中不得残留固定假提升的模拟 A/B。
"""

from pathlib import Path


def test_no_simulate_ab_test_in_source():
    app_dir = Path(__file__).resolve().parent.parent / "app"
    offenders = []
    for py in app_dir.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        if "_simulate_ab_test" in text:
            offenders.append(f"{py}: _simulate_ab_test")
        if "improvements = [5.0, 3.0, 1.0]" in text:
            offenders.append(f"{py}: 固定假提升数组")
    assert offenders == [], f"发现假 A/B 残留: {offenders}"


def test_orchestrator_uses_real_ab_service():
    orchestrator = (
        Path(__file__).resolve().parent.parent
        / "app" / "services" / "evolution_orchestrator.py"
    ).read_text(encoding="utf-8")
    assert "PromptABTestService" in orchestrator
    assert "run_ab_test" in orchestrator
