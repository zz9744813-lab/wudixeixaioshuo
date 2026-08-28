---
id: scene_technique
version: "1.0"
purpose: Mine candidate writing techniques (spec §15)
model_class: structured
input_schema: {scene_text: str}
output_schema: {candidates: [{name, category, mechanism, evidence}]}
change_reason: initial EPIC-C prompt
---

你从 Scene 中挖掘**候选写作技法**（spec §15）。技法不是标签，需说明机制。
category 取一级分类之一: Information, Suspense, Mystery, Foreshadow, Reveal, Payoff,
Conflict, Escalation, Characterization, Relationship, Emotion, Pacing, Dialogue, POV,
Scene Structure, Chapter Hook, Worldbuilding, Action, Comedy, Horror, Romance,
Erotic Tension, Tragedy, Twist, Misdirection, Reward, Loss, Progression, Power Fantasy。

对每条候选给出 name、category、mechanism（机制要点列表）、evidence（文中证据）。

只输出 JSON: {"candidates": [...]}
