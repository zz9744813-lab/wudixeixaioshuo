---
id: scene_counterinterpretation
version: "1.0"
purpose: Propose alternative interpretations (spec §16 PASS-16)
model_class: structured
input_schema: {scene_text: str}
output_schema: {alternatives: [str]}
change_reason: initial EPIC-C prompt
---

你为上述 Scene 分析提出**其他可能的解释**（spec §16 PASS-16）。目的是对抗单一解读，
避免把作者结构误认为角色真实动机（spec P-05）。

列出 1-3 条与主流解读不同的合理解释（每条一句话）。

只输出 JSON: {"alternatives": [...]}
