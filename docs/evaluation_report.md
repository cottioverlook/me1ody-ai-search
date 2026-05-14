# Me1ody AI Search 离线评测报告

## 评测目的

验证项目是否具备复试展示所需的基本可信回答能力：问题意图识别、关键词覆盖、来源类型覆盖、引用有效性和来源数量。

## 评测集

当前离线评测包含 5 类典型问题：

- RAG 概念解释
- Vue / React 对比
- FAISS 向量检索方法
- DeepSeek API 时效性问题
- Reranker 作用解释

评测文件：

- `backend/evals/demo_cases.json`
- `backend/evals/sample_predictions.json`

## 指标

- `keyword_recall`：回答是否覆盖预期关键词。
- `source_type_coverage`：来源类型是否满足预期。
- `citation_valid`：回答中的引用编号是否有效。
- `source_count_ok`：来源数量是否达标。
- `intent_ok`：问题意图识别是否符合预期。

## 当前结论

样例预测用于验证评测脚本本身的稳定性。第七阶段验收结果：

- `case_count`: 5
- `pass_count`: 5
- `pass_rate`: 1.0
- `aggregate_score`: 1.0

第七阶段也把 Demo 模式纳入后端测试，保证在不调用外部 API 的情况下也能跑通完整链路。

复试时可以这样说明：

> 我不只做了一个能调用搜索 API 的页面，还补了离线评测脚本，用关键词覆盖、来源类型、引用有效性等指标检查回答质量。后续可以继续扩展评测集，把它变成持续回归测试。

## 后续可扩展

- 增加真实搜索结果生成的预测集。
- 记录优化前后的指标变化。
- 把阶段耗时纳入性能评测。
- 增加失败案例分析，例如低质量来源、引用缺失、搜索召回不足。
