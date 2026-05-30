"""
P3 商业 Critic Rubric 测试
验证 fallback Critic Prompt 包含追读欲、情绪钩子、主角主动性、总编指令达成度等维度。
"""

from app.services.pipeline_service import PipelineService


def test_critic_prompt_contains_commercial_dimensions():
    service = PipelineService()
    prompt = service._build_critic_rubric_prompt("第一章", "一段正文内容")

    assert "reader_addiction" in prompt
    assert "emotional_hook_strength" in prompt
    assert "protagonist_agency" in prompt
    assert "conflict_density" in prompt
    assert "information_gain" in prompt
    assert "editor_directive_fulfillment" in prompt
    # 中文锚点说明
    assert "追读欲" in prompt
    assert "情绪钩子强度" in prompt
    assert "总编指令达成度" in prompt


def test_critic_prompt_contains_commercial_diagnosis():
    service = PipelineService()
    prompt = service._build_critic_rubric_prompt("第一章", "一段正文内容")
    assert "commercial_diagnosis" in prompt
    assert "reader_drop_risk" in prompt
    assert "next_chapter_pull" in prompt
