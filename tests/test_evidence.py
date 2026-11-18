import unittest
from datetime import date

from signal_lab.analysis import assess_usability, build_conclusion, link_evidence
from signal_lab.records import Correction, Observation, Translation
from signal_lab.report import assess_report_usability, create_report, publish_report


def make_observation(observation_id, source_id, stance="support", **kwargs):
    return Observation(
        observation_id, source_id, date(2026, 11, 1), "topic", 1,
        stance=stance, **kwargs,
    )


class EvidenceLinkTests(unittest.TestCase):
    def test_links_keep_supporting_and_contradicting_side_by_side(self):
        rows = [
            make_observation("a", "desk-1"),
            make_observation("b", "desk-2", stance="contradict"),
        ]
        links = link_evidence(rows, "topic")
        roles = {link.observation_id: link.role for link in links}
        self.assertEqual(roles, {"a": "supporting", "b": "contradicting"})

    def test_basis_cites_excerpt_and_translation(self):
        rows = [make_observation(
            "a", "desk", language="zh", excerpt="原文表述",
            translation=Translation("desk-zh", "translated text", status="verified"),
        )]
        link = link_evidence(rows, "topic")[0]
        self.assertIn("原文表述", link.basis)
        self.assertIn("desk-zh", link.basis)


class ConclusionTests(unittest.TestCase):
    def test_conclusion_traces_back_to_supporting_observations(self):
        rows = [
            make_observation("a", "desk-1", excerpt="甲"),
            make_observation("b", "desk-2", excerpt="乙"),
        ]
        conclusion = build_conclusion("c-1", "判断", "topic", "全球 / 2026-11", rows)
        self.assertEqual(conclusion.status, "confirmed")
        self.assertEqual(
            {link.observation_id for link in conclusion.evidence}, {"a", "b"},
        )
        self.assertTrue(all(link.basis for link in conclusion.evidence))

    def test_minority_contradiction_is_not_overridden_by_majority(self):
        rows = [
            make_observation("a", "desk-1"),
            make_observation("b", "desk-2"),
            make_observation("c", "desk-3"),
            make_observation("d", "desk-4", stance="contradict"),
        ]
        with self.assertRaises(ValueError):
            build_conclusion("c-1", "判断", "topic", "范围", rows)
        conclusion = build_conclusion(
            "c-1", "判断", "topic", "范围", rows, rationale="反证来源单一且未获独立印证",
        )
        self.assertEqual(conclusion.status, "contested")
        contradicting = [link for link in conclusion.evidence if link.role == "contradicting"]
        self.assertEqual([link.observation_id for link in contradicting], ["d"])

    def test_ambiguous_translation_is_listed_as_open_question(self):
        rows = [
            make_observation("a", "desk-1"),
            make_observation(
                "b", "desk-2", language="zh",
                translation=Translation("desk-zh", "译文", status="ambiguous", ambiguity_notes="关键动词可两解"),
            ),
        ]
        conclusion = build_conclusion("c-1", "判断", "topic", "范围", rows)
        self.assertEqual(conclusion.status, "provisional")
        self.assertTrue(any("歧义" in item for item in conclusion.open_questions))

    def test_insufficient_coverage_is_listed_as_open_question(self):
        rows = [make_observation("a", "desk-1"), make_observation("b", "desk-1")]
        conclusion = build_conclusion("c-1", "判断", "topic", "范围", rows)
        self.assertEqual(conclusion.status, "provisional")
        self.assertTrue(any("支撑来源不足" in item for item in conclusion.open_questions))

    def test_conclusion_requires_supporting_evidence(self):
        rows = [make_observation("a", "desk-1", stance="contradict")]
        with self.assertRaises(ValueError):
            build_conclusion("c-1", "判断", "topic", "范围", rows)

    def test_corrected_observation_is_excluded_from_current_conclusion(self):
        rows = [
            make_observation("a", "desk-1"),
            make_observation("b", "desk-2"),
        ]
        corrections = [Correction("cor-1", "desk-2", date(2026, 11, 5), ("b",), "来源撤回原表述")]
        conclusion = build_conclusion(
            "c-1", "判断", "topic", "范围", rows, corrections=corrections,
        )
        self.assertEqual({link.observation_id for link in conclusion.evidence}, {"a"})
        self.assertTrue(any("已被来源更正" in item for item in conclusion.open_questions))

    def test_usability_assessment_flags_corrected_support(self):
        rows = [
            make_observation("a", "desk-1"),
            make_observation("b", "desk-2"),
        ]
        conclusion = build_conclusion("c-1", "判断", "topic", "范围", rows)
        corrections = [Correction("cor-1", "desk-2", date(2026, 11, 5), ("b",), "来源撤回原表述")]
        result = assess_usability(conclusion, corrections)
        self.assertFalse(result["usable"])
        self.assertEqual(result["impacted_evidence"][0]["observation_id"], "b")
        self.assertEqual(conclusion.status, "confirmed")  # 评估不修改结论本身


class PublishedReportTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            make_observation("a", "desk-1", excerpt="甲"),
            make_observation("b", "desk-2", excerpt="乙"),
        ]
        self.conclusion = build_conclusion("c-1", "判断", "topic", "范围", self.rows)
        self.report = create_report(
            "r-1", "标题", "2026-11-01", "2026-11-30",
            ["desk-1", "desk-2"], {"topic": 2}, conclusions=[self.conclusion],
        )

    def test_publish_freezes_evidence_snapshot(self):
        published = publish_report(self.report, self.rows)
        self.assertTrue(published.published)
        self.assertEqual(
            {obs.observation_id for obs in published.evidence_snapshot}, {"a", "b"},
        )

    def test_publish_requires_all_referenced_observations(self):
        with self.assertRaises(ValueError):
            publish_report(self.report, self.rows[:1])

    def test_published_report_cannot_be_republished(self):
        published = publish_report(self.report, self.rows)
        with self.assertRaises(ValueError):
            publish_report(published, self.rows)

    def test_correction_marks_usability_but_published_report_stays_intact(self):
        published = publish_report(self.report, self.rows)
        corrections = [Correction("cor-1", "desk-2", date(2026, 11, 5), ("b",), "来源撤回原表述")]
        assessment = assess_report_usability(published, corrections)
        self.assertEqual(len(assessment), 1)
        self.assertFalse(assessment[0]["usable"])
        # 已发布报告保留当时看到的证据与理由
        snapshot_ids = {obs.observation_id for obs in published.evidence_snapshot}
        self.assertEqual(snapshot_ids, {"a", "b"})
        self.assertEqual(published.conclusions[0].status, "confirmed")
        self.assertEqual(published.conclusions[0].evidence, self.conclusion.evidence)


if __name__ == "__main__":
    unittest.main()
