---
id: scene_goal
version: "1.0"
purpose: Extract character goals and lifecycle (spec §9.2, §72)
model_class: structured
input_schema: {scene_text: str}
output_schema: {goals: [{character, statement, lifecycle, strength}]}
change_reason: initial EPIC-C prompt
---

你抽取一个 Scene 中角色的**目标（Goal）及其生命周期**（spec §9.2, §72）。
lifecycle 取: active / blocked / completed。strength 表示目标强度（0-1）。

对每个有名字的角色，给出其当前目标 statement、lifecycle、strength。

只输出 JSON: {"goals": [...]}
