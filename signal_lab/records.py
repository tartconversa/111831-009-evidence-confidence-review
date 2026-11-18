from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Source:
    source_id: str
    region: str
    language: str
    active: bool = True
    quality_notes: str = ""  # 采编流程、过往更正记录等来源质量说明


@dataclass(frozen=True)
class Translation:
    """观察所依据的译文记录。"""

    translator: str
    text: str
    status: str = "unverified"  # verified / unverified / ambiguous
    ambiguity_notes: str = ""  # 歧义说明


@dataclass(frozen=True)
class Observation:
    observation_id: str
    source_id: str
    observed_on: date
    topic: str
    value: float
    region: str = "global"
    language: str = "en"
    excerpt: str = ""  # 原文摘录
    translation: Translation | None = None
    stance: str = "neutral"  # support / contradict / neutral，相对主题工作判断的方向


@dataclass(frozen=True)
class Correction:
    """来源对已发布观察的更正。"""

    correction_id: str
    source_id: str
    issued_on: date
    observation_ids: tuple[str, ...]  # 受影响的观察
    summary: str


@dataclass(frozen=True)
class EvidenceLink:
    """结论与具体观察之间的可追溯关联。"""

    observation_id: str
    role: str  # supporting / contradicting / context
    basis: str = ""  # 依赖的原文或翻译依据


@dataclass(frozen=True)
class Conclusion:
    """一条可回溯、可复核的分析结论。"""

    conclusion_id: str
    statement: str
    topic: str
    scope: str  # 判断适用的范围（地区、时段、语言等）
    evidence: tuple[EvidenceLink, ...]
    rationale: str = ""  # 存在相反材料时保留当前解读的理由
    open_questions: tuple[str, ...] = ()  # 仍待确认的部分
    status: str = "provisional"  # confirmed / provisional / contested
