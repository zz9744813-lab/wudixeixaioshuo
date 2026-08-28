---
id: scene_relationship
version: "1.0"
purpose: Extract relationship changes (spec §11)
model_class: structured
input_schema: {scene_text: str}
output_schema: {changes: [{source, target, dimension, delta, cause, last_changed_scene}]}
change_reason: initial EPIC-C prompt
---

你抽取一个 Scene 中**角色间关系的变化**（spec §11）。关系不是单一好感度，而是多个维度:
trust, attachment, respect, admiration, fear, resentment, dependency, obligation,
competition, jealousy, intimacy, sexual_tension, power, predictability。

对每条变化给出 source、target、dimension、delta（变化量，-1 到 1，正向为增强）、
cause（原因，一句话）、last_changed_scene 留空。

只输出 JSON: {"changes": [...]}
