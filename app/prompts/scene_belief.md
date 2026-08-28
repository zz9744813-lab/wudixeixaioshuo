---
id: scene_belief
version: "1.0"
purpose: Extract belief updates per character (spec §9.2)
model_class: structured
input_schema: {scene_text: str}
output_schema: {beliefs: [{character, proposition, probability, source, confidence}]}
change_reason: initial EPIC-C prompt
---

你抽取一个 Scene 中角色的**信念变化**（spec §9.2）。信念是角色对某事"认为是否成立"，
用 probability（0=完全不信，1=完全相信）表示。

对每条信念给出 character、proposition（信念命题）、probability、source（证据来源，可留空）、
confidence（你判断该信念确实存在的把握，0-1）。

只输出 JSON: {"beliefs": [...]}
