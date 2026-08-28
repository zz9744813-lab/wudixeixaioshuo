---
id: scene_knowledge
version: "1.0"
purpose: Track knowledge-state changes per character (spec §10)
model_class: structured
input_schema: {scene_text: str}
output_schema: {updates: [{fact, character, status, confidence, source_span}]}
change_reason: initial EPIC-C prompt
---

你追踪一个 Scene 中**每个角色对某个事实的知识状态变化**（spec §10）。同一个事实对不同角色
状态可能不同: KNOWN / SUSPECTED / FALSE_BELIEF / UNKNOWN / EXPOSED / BELIEVED / DISBELIEVED。

对每条知识更新给出 fact（事实描述）、character（角色名）、status（上述枚举之一）、
confidence（0-1）。注意区分"角色知道"与"读者知道"。

只输出 JSON: {"updates": [...]}
