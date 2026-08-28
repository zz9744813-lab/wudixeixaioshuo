---
id: scene_emotion
version: "1.0"
purpose: Extract emotion causal chains (spec §12)
model_class: structured
input_schema: {scene_text: str}
output_schema: {emotions: [{character, type, intensity, trigger, appraisal, action_tendency, evidence}]}
change_reason: initial EPIC-C prompt
---

你分析一个 Scene 中角色的**情绪因果链**（spec §12），禁止只打情绪标签。
对每种情绪给出:
- character, type（anger/sadness/fear/joy/anxiety/shame/...）
- intensity（0-1）
- trigger（触发事件，一句话）
- appraisal（评价维度 dict，如 {blame: "B", goal_obstruction: 0.7}）
- action_tendency（行为倾向 dict，如 {confront: 0.6, withdraw: 0.2}）
- evidence（支撑该判断的文本线索列表）

只输出 JSON: {"emotions": [...]}
