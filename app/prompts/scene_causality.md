---
id: scene_causality
version: "1.0"
purpose: Extract causal edges (spec §13)
model_class: structured
input_schema: {scene_text: str}
output_schema: {edges: [{frm, to, type, necessity, sufficiency, confidence, evidence, alternatives}]}
change_reason: initial EPIC-C prompt
---

你抽取一个 Scene 内的**因果边**（spec §13）。注意:相邻事件不等于因果。

边类型 type: physical_cause, informational_cause, psychological_cause, social_cause,
resource_cause, goal_cause, constraint_cause, authorial_structure, temporal_only, correlation_only。

对每条边给出 frm（原因事件/状态）、to（结果事件/状态）、type、necessity（0-1）、
suffiency→sufficiency（0-1）、confidence（0-1）、evidence（文本证据列表）、
alternatives（其他可能解释）。若只是时间先后，type 用 temporal_only。

只输出 JSON: {"edges": [...]}
