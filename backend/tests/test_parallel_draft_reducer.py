"""
P7 DraftReducer 选优测试
"""

import asyncio

from app.services.draft_reducer_service import DraftReducerService


_CANDIDATES = [
    {
        "candidate_id": "draft_candidate_1", "strategy": "节奏最快",
        "content": "正文一", "score": 78,
        "score_breakdown": {"reader_addiction": 70, "ending_hook": 72,
                            "editor_directive_fulfillment": 70, "continuity": 80},
        "cost": 0.1,
    },
    {
        "candidate_id": "draft_candidate_2", "strategy": "情绪最强",
        "content": "正文二", "score": 85,
        "score_breakdown": {"reader_addiction": 88, "ending_hook": 86,
                            "editor_directive_fulfillment": 84, "continuity": 82},
        "cost": 0.12,
    },
    {
        "candidate_id": "draft_candidate_3", "strategy": "伏笔最密",
        "content": "正文三", "score": 80,
        "score_breakdown": {"reader_addiction": 75, "ending_hook": 78,
                            "editor_directive_fulfillment": 90, "continuity": 85},
        "cost": 0.11,
    },
]


def test_select_best_picks_highest_rank(db_session):
    service = DraftReducerService(db_session)
    result = asyncio.run(service.select_best_candidate(
        project_id=1, chapter_id=1, candidates=_CANDIDATES,
    ))
    assert result["selected"]["candidate_id"] == "draft_candidate_2"
    assert len(result["ranking"]) == 3
    assert result["reason"]


def test_select_best_empty(db_session):
    service = DraftReducerService(db_session)
    result = asyncio.run(service.select_best_candidate(
        project_id=1, chapter_id=1, candidates=[],
    ))
    assert result["selected"] is None


def test_cost_penalty_affects_rank(db_session):
    service = DraftReducerService(db_session)
    candidates = [
        {"candidate_id": "a", "strategy": "低成本", "content": "x", "score": 82,
         "score_breakdown": {"reader_addiction": 82, "ending_hook": 82,
                             "editor_directive_fulfillment": 82, "continuity": 82},
         "cost": 0.0},
        {"candidate_id": "b", "strategy": "高成本", "content": "y", "score": 82,
         "score_breakdown": {"reader_addiction": 82, "ending_hook": 82,
                             "editor_directive_fulfillment": 82, "continuity": 82},
         "cost": 2.0},
    ]
    result = asyncio.run(service.select_best_candidate(
        project_id=1, chapter_id=1, candidates=candidates,
    ))
    # 同分情况下，低成本候选应排名更高
    assert result["selected"]["candidate_id"] == "a"


def test_merge_candidates(db_session):
    service = DraftReducerService(db_session)
    result = asyncio.run(service.merge_candidates(
        project_id=1, chapter_id=1, candidates=_CANDIDATES,
        selected_ids=["draft_candidate_1", "draft_candidate_3"],
    ))
    assert "正文一" in result["content"]
    assert "正文三" in result["content"]
    assert set(result["merged_ids"]) == {"draft_candidate_1", "draft_candidate_3"}
