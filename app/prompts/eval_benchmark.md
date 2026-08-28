---
id: eval_benchmark
version: "1.0"
purpose: Answer one benchmark case about a scene (spec §24, §47)
model_class: reasoning
input_schema: {scene_text: str, question: str, expected_format: dict}
output_schema: {answer: dict}
change_reason: initial EPIC-E prompt
---

你回答关于某个 Scene 的基准测试问题（spec §24）。上下文包含场景文本与问题。
expected_format 描述答案的键与类型（不包含答案本身）。

严格按 expected_format 的键输出 answer 对象；不确定的键填 null，不要猜（spec §71）。
只输出 JSON: {"answer": {...}}
