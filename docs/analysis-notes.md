# 分析口径

当前项目的观察重点是source evidence and conclusion。来源信息、观测记录与分析输出分别保存；报告保留生成时使用的来源标识，便于研究人员回看数据范围。输入观测的数值含义由调用方提供，项目不将报道计数解释为受众态度或传播因果。

## 证据与结论的回溯口径

- 每条结论（Conclusion）通过证据链（EvidenceLink）记录支撑、相反与背景证据，并注明依赖的原文摘录与译文依据；来源记录保存质量说明（quality_notes）。
- 相反材料与支撑材料在结论中并列保存。证据数量不影响结论状态：存在相反证据时结论为 contested，且必须写明保留当前解读的理由（rationale），少数反证不被多数覆盖。
- 来源更正（Correction）会影响当前结论的可用性评估（assess_usability / assess_report_usability）；构建当前结论时被更正的观察不纳入证据，并在 open_questions 中说明。
- 已发布报告（publish_report）冻结发布时引用的证据快照与理由，之后不因更正而改写；更正只体现在后续可用性评估中。
- 数据不足或翻译存在歧义时，结论的 open_questions 如实列出仍待确认的部分（翻译歧义、译文未核校、独立来源不足），结论状态相应为 provisional。
