---
id: scene_perception
version: "1.0"
purpose: Extract what each character perceived in a Scene (spec §16 PASS-04)
model_class: structured
input_schema: {scene_text: str}
output_schema: {perceptions: [{character, perceived_event, content}]}
change_reason: initial EPIC-C prompt
---

你分析一个 Scene 中每个角色**感知到了什么**（spec §16 PASS-04）。感知不等于事实，
可能是误解或部分信息。

对出现的每个有名字的角色，给出它感知到的内容 content（一句话），perceived_event 留空。
若某角色未感知关键信息，也要说明。

只输出 JSON: {"perceptions": [...]}
