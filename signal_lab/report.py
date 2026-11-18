from dataclasses import dataclass, replace
from datetime import datetime, timezone

from .analysis import assess_usability
from .records import Conclusion, Observation


@dataclass(frozen=True)
class AnalysisReport:
    report_id: str
    title: str
    period_start: str
    period_end: str
    source_ids: tuple[str, ...]
    measures: dict[str, float]
    created_at: str
    conclusions: tuple[Conclusion, ...] = ()
    evidence_snapshot: tuple[Observation, ...] = ()  # 发布时冻结的证据副本
    published: bool = False


def create_report(report_id, title, period_start, period_end, source_ids, measures, *, conclusions=()):
    return AnalysisReport(
        report_id=report_id, title=title, period_start=period_start, period_end=period_end,
        source_ids=tuple(sorted(set(source_ids))), measures=dict(measures),
        created_at=datetime.now(timezone.utc).isoformat(),
        conclusions=tuple(conclusions),
    )


def publish_report(report, observations):
    """冻结报告引用的证据并标记为已发布；已发布报告不可再修改。"""
    if report.published:
        raise ValueError("报告已发布，不能重复发布或修改")
    referenced = {
        link.observation_id
        for conclusion in report.conclusions
        for link in conclusion.evidence
    }
    snapshot = tuple(sorted(
        (observation for observation in observations if observation.observation_id in referenced),
        key=lambda observation: observation.observation_id,
    ))
    missing = referenced - {observation.observation_id for observation in snapshot}
    if missing:
        raise ValueError(f"缺少证据观察：{sorted(missing)}")
    return replace(report, evidence_snapshot=snapshot, published=True)


def assess_report_usability(report, corrections):
    """对照更正确认已发布结论是否仍可使用；报告与其证据快照保持不变。"""
    return tuple(assess_usability(conclusion, corrections) for conclusion in report.conclusions)
