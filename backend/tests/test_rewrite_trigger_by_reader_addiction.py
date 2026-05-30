"""
P3 低追读欲触发 Rewrite 测试
验证 overall_score=82 但 reader_addiction=68 时仍触发 Rewrite，且原因可见。
"""

from app.services.pipeline_service import PipelineService


def test_should_rewrite_triggered_by_low_reader_addiction():
    service = PipelineService()
    critic_result = {
        "score": 82,
        "score_breakdown": {
            "reader_addiction": 68,
            "emotional_hook_strength": 80,
            "ending_hook": 82,
            "editor_directive_fulfillment": 80,
            "protagonist_agency": 80,
        },
    }
    need_rewrite, reasons = service._should_rewrite(critic_result)
    assert need_rewrite is True
    assert any("追读欲" in r for r in reasons)


def test_should_rewrite_triggered_by_directive_fulfillment():
    service = PipelineService()
    critic_result = {
        "score": 85,
        "score_breakdown": {
            "reader_addiction": 80,
            "ending_hook": 80,
            "editor_directive_fulfillment": 60,
        },
    }
    need_rewrite, reasons = service._should_rewrite(critic_result)
    assert need_rewrite is True
    assert any("总编指令" in r for r in reasons)


def test_should_not_rewrite_when_all_high():
    service = PipelineService()
    critic_result = {
        "score": 88,
        "score_breakdown": {
            "reader_addiction": 85,
            "emotional_hook_strength": 84,
            "ending_hook": 86,
            "editor_directive_fulfillment": 82,
            "protagonist_agency": 83,
        },
    }
    need_rewrite, reasons = service._should_rewrite(critic_result)
    assert need_rewrite is False
    assert reasons == []


def test_should_rewrite_low_total_score():
    service = PipelineService()
    need_rewrite, reasons = service._should_rewrite({"score": 70, "score_breakdown": {}})
    assert need_rewrite is True
    assert any("总分不足" in r for r in reasons)
