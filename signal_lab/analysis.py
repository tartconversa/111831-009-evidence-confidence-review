from collections import defaultdict

from .records import Conclusion, EvidenceLink


def compare_periods(observations, start, end, *, region=None):
    """汇总两个周期内的观察值与来源覆盖数量。"""
    periods = ((start[0], start[1]), (end[0], end[1]))
    totals = [defaultdict(float), defaultdict(float)]
    sources = [defaultdict(set), defaultdict(set)]
    for observation in observations:
        if region is not None and observation.region != region:
            continue
        key = (observation.observed_on.year, observation.observed_on.month)
        if key not in periods:
            continue
        slot = periods.index(key)
        totals[slot][observation.topic] += observation.value
        sources[slot][observation.topic].add(observation.source_id)
    topics = sorted(set(totals[0]) | set(totals[1]))
    return {topic: {
        "start_value": totals[0][topic], "end_value": totals[1][topic],
        "start_sources": len(sources[0][topic]), "end_sources": len(sources[1][topic]),
    } for topic in topics}


_STANCE_TO_ROLE = {"support": "supporting", "contradict": "contradicting", "neutral": "context"}


def _basis_for(observation):
    """生成证据所依赖的原文与翻译说明。"""
    parts = [f"{observation.language} 原文"]
    if observation.excerpt:
        parts.append(f"摘录：{observation.excerpt}")
    translation = observation.translation
    if translation is not None:
        parts.append(f"译文（{translation.translator}，{translation.status}）")
        if translation.ambiguity_notes:
            parts.append(f"歧义：{translation.ambiguity_notes}")
    return "；".join(parts)


def link_evidence(observations, topic):
    """按主题收集证据链，支撑与相反材料并列保留，不做多数取舍。"""
    links = []
    for observation in observations:
        if observation.topic != topic:
            continue
        role = _STANCE_TO_ROLE.get(observation.stance, "context")
        links.append(EvidenceLink(observation.observation_id, role, _basis_for(observation)))
    return tuple(links)


def build_conclusion(conclusion_id, statement, topic, scope, observations, *, rationale="", corrections=()):
    """汇总主题证据并推导结论状态。

    规则：
    - 至少一条支撑证据，否则无法形成结论；
    - 存在相反证据时状态为 contested，且必须说明保留当前解读的理由；
    - 证据数量不影响状态，少数反证不被多数覆盖；
    - 已被来源更正的观察不纳入证据，并在 open_questions 中说明；
    - 翻译歧义、译文未核校、独立来源不足都会写入 open_questions。
    """
    by_id = {observation.observation_id: observation for observation in observations}
    corrected_ids = {
        observation_id
        for correction in corrections
        for observation_id in correction.observation_ids
    }
    links = []
    open_questions = []
    for observation in observations:
        if observation.topic != topic:
            continue
        if observation.observation_id in corrected_ids:
            open_questions.append(f"观察 {observation.observation_id} 已被来源更正，未纳入证据")
            continue
        role = _STANCE_TO_ROLE.get(observation.stance, "context")
        links.append(EvidenceLink(observation.observation_id, role, _basis_for(observation)))
        translation = observation.translation
        if translation is not None and translation.status == "ambiguous":
            open_questions.append(f"观察 {observation.observation_id} 的翻译存在歧义：{translation.ambiguity_notes}")
        elif translation is not None and translation.status == "unverified":
            open_questions.append(f"观察 {observation.observation_id} 的译文尚未核校")

    supporting = [link for link in links if link.role == "supporting"]
    contradicting = [link for link in links if link.role == "contradicting"]
    if not supporting:
        raise ValueError("结论缺少支撑证据，无法形成判断")
    if contradicting and not rationale:
        raise ValueError("存在相反材料，必须说明保留当前解读的理由")

    independent_sources = {by_id[link.observation_id].source_id for link in supporting}
    if len(independent_sources) < 2:
        open_questions.append(f"支撑来源不足：仅 {len(independent_sources)} 个独立来源")

    if contradicting:
        status = "contested"
    elif open_questions:
        status = "provisional"
    else:
        status = "confirmed"
    return Conclusion(
        conclusion_id=conclusion_id, statement=statement, topic=topic, scope=scope,
        evidence=tuple(links), rationale=rationale,
        open_questions=tuple(open_questions), status=status,
    )


def assess_usability(conclusion, corrections):
    """评估来源更正对结论可用性的影响，不修改结论本身。"""
    by_observation = {}
    for correction in corrections:
        for observation_id in correction.observation_ids:
            by_observation.setdefault(observation_id, []).append(correction)
    impacted = []
    for link in conclusion.evidence:
        for correction in by_observation.get(link.observation_id, []):
            impacted.append({
                "observation_id": link.observation_id,
                "role": link.role,
                "correction_id": correction.correction_id,
                "summary": correction.summary,
            })
    supporting_hit = any(item["role"] == "supporting" for item in impacted)
    return {
        "conclusion_id": conclusion.conclusion_id,
        "usable": not supporting_hit,
        "impacted_evidence": tuple(impacted),
    }
