"""
Comprehensive test suite for Multi-Agent Research Intelligence Platform.
Run: .venv/bin/python -m pytest tests/ -v
Or: .venv/bin/python tests/test_agents.py
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.communication import bus, AgentStatus, MessageType, CommunicationBus
from core.state import (
    ResearchState, ResearchPlan, ResearchFinding,
    FactCheckResult, ReviewResult
)


class TestCommunicationBus(unittest.TestCase):
    def setUp(self):
        self.bus = CommunicationBus()

    def test_post_message(self):
        msg = self.bus.post("planner", "Test message", message_type=MessageType.SYSTEM)
        self.assertEqual(msg.sender, "planner")
        self.assertEqual(msg.content, "Test message")
        self.assertEqual(len(self.bus.get_messages()), 1)

    def test_agent_status_transitions(self):
        self.bus.set_agent_status("planner", AgentStatus.WORKING, task="Research planning")
        self.assertEqual(self.bus.agent_states["planner"].status, AgentStatus.WORKING)
        self.assertEqual(self.bus.agent_states["planner"].current_task, "Research planning")

        self.bus.set_agent_status("planner", AgentStatus.COMPLETED, output_preview="Done")
        self.assertEqual(self.bus.agent_states["planner"].status, AgentStatus.COMPLETED)
        self.assertIsNotNone(self.bus.agent_states["planner"].end_time)

    def test_reset(self):
        self.bus.post("planner", "Test", message_type=MessageType.SYSTEM)
        self.bus.reset()
        self.assertEqual(len(self.bus.get_messages()), 0)

    def test_timeline_entries(self):
        self.bus.post("researcher", "Searching…", message_type=MessageType.TASK_ASSIGN)
        entries = self.bus.get_timeline_entries()
        self.assertEqual(len(entries), 1)
        self.assertIn("icon", entries[0])
        self.assertIn("content", entries[0])

    def test_all_agents_initialized(self):
        agents = self.bus.get_agent_states()
        required = ["planner", "researcher", "analyst", "writer", "fact_checker", "reviewer"]
        for a in required:
            self.assertIn(a, agents, f"Agent {a} not initialized")

    def test_elapsed_time(self):
        import time
        self.bus.set_agent_status("researcher", AgentStatus.WORKING)
        time.sleep(0.05)
        elapsed = self.bus.agent_states["researcher"].elapsed_seconds
        self.assertGreater(elapsed, 0)


class TestResearchState(unittest.TestCase):
    def test_initial_state(self):
        state = ResearchState(session_id="test-001", topic="Quantum Computing", depth="standard")
        self.assertEqual(state.topic, "Quantum Computing")
        self.assertEqual(state.depth, "standard")
        self.assertEqual(state.review_iteration, 0)
        self.assertEqual(len(state.completed_agents), 0)

    def test_mark_agent_complete(self):
        state = ResearchState(session_id="t", topic="Test")
        state.mark_agent_complete("planner")
        state.mark_agent_complete("researcher")
        self.assertIn("planner", state.completed_agents)
        self.assertIn("researcher", state.completed_agents)
        # Idempotent
        state.mark_agent_complete("planner")
        self.assertEqual(state.completed_agents.count("planner"), 1)

    def test_mark_agent_failed(self):
        state = ResearchState(session_id="t", topic="Test")
        state.mark_agent_failed("researcher", "Network timeout")
        self.assertIn("researcher", state.failed_agents)
        self.assertEqual(len(state.errors), 1)
        self.assertIn("Network timeout", state.errors[0])

    def test_to_dict(self):
        state = ResearchState(session_id="test-001", topic="AI")
        state.review_result = ReviewResult(score=85, approved=True)
        d = state.to_dict()
        self.assertEqual(d["topic"], "AI")
        self.assertEqual(d["quality_score"], 85)
        self.assertIn("completed_agents", d)

    def test_research_plan(self):
        plan = ResearchPlan(
            topic="AI",
            objectives=["Understand AI", "Analyze applications"],
            sub_questions=["What is AI?", "How does ML work?"],
            methodology="Literature review",
            scope="Computer science",
            expected_sections=["Intro", "Analysis", "Conclusion"],
        )
        self.assertEqual(len(plan.objectives), 2)
        self.assertEqual(len(plan.sub_questions), 2)

    def test_fact_check_result(self):
        fc = FactCheckResult(
            claim="AI achieves 95% accuracy",
            status="verified",
            evidence="Multiple studies confirm",
            confidence=0.9,
        )
        self.assertEqual(fc.status, "verified")
        self.assertEqual(fc.confidence, 0.9)


class TestPlannerAgent(unittest.TestCase):
    @patch("agents.planner.call_llm_with_retry")
    def test_planner_success(self, mock_llm):
        mock_llm.return_value = """{
            "objectives": ["Understand topic", "Analyze trends"],
            "sub_questions": ["What is it?", "How does it work?"],
            "methodology": "Literature review and web research",
            "scope": "Comprehensive technical overview",
            "expected_sections": ["Introduction", "Background", "Analysis", "Conclusion"]
        }"""
        from agents.planner import run_planner
        state = ResearchState(session_id="t", topic="Machine Learning", depth="quick")
        result = run_planner(state)
        self.assertIsNotNone(result.plan)
        self.assertEqual(len(result.plan.objectives), 2)
        self.assertIn("planner", result.completed_agents)

    @patch("agents.planner.call_llm_with_retry")
    def test_planner_fallback_on_bad_json(self, mock_llm):
        mock_llm.return_value = "This is not valid JSON at all"
        from agents.planner import run_planner
        state = ResearchState(session_id="t", topic="Blockchain", depth="quick")
        result = run_planner(state)
        # Should fall back gracefully
        self.assertIsNotNone(result.plan)
        self.assertGreater(len(result.plan.objectives), 0)
        self.assertIn("planner", result.completed_agents)

    @patch("agents.planner.call_llm_with_retry")
    def test_planner_failure(self, mock_llm):
        mock_llm.side_effect = RuntimeError("504 DEADLINE_EXCEEDED")
        from agents.planner import run_planner
        state = ResearchState(session_id="t", topic="Test", depth="quick")
        result = run_planner(state)
        self.assertIn("planner", result.failed_agents)


class TestFactCheckerAgent(unittest.TestCase):
    @patch("agents.fact_checker.call_llm_with_retry")
    def test_fact_checker_success(self, mock_llm):
        mock_llm.return_value = """[
            {"claim": "AI improves diagnostics", "status": "verified", "evidence": "Studies confirm", "confidence": 0.9},
            {"claim": "AI cures cancer", "status": "unsupported", "evidence": "Not in research data", "confidence": 0.1}
        ]"""
        from agents.fact_checker import run_fact_checker
        state = ResearchState(
            session_id="t", topic="AI",
            raw_research="AI is effective in diagnostics.",
            draft_report="## Report\nAI improves diagnostics. AI also cures cancer."
        )
        result = run_fact_checker(state)
        self.assertEqual(len(result.fact_check_results), 2)
        self.assertEqual(result.fact_check_results[0].status, "verified")
        self.assertEqual(result.fact_check_results[1].status, "unsupported")

    @patch("agents.fact_checker.call_llm_with_retry")
    def test_fact_checker_bad_json_fallback(self, mock_llm):
        mock_llm.return_value = "Invalid JSON response from LLM"
        from agents.fact_checker import run_fact_checker
        state = ResearchState(
            session_id="t", topic="AI",
            raw_research="AI data",
            draft_report="## Report\nSome claims here."
        )
        result = run_fact_checker(state)
        # Should produce at least one fallback result
        self.assertGreater(len(result.fact_check_results), 0)


class TestReviewerAgent(unittest.TestCase):
    @patch("agents.reviewer.call_llm_with_retry")
    def test_reviewer_approved(self, mock_llm):
        mock_llm.return_value = """{
            "accuracy_score": 18, "completeness_score": 17, "clarity_score": 16,
            "structure_score": 15, "depth_score": 14,
            "total_score": 80,
            "strengths": ["Well structured", "Comprehensive analysis"],
            "weaknesses": ["Could use more citations"],
            "improvement_instructions": "Add more specific references",
            "approved": true
        }"""
        from agents.reviewer import run_reviewer
        state = ResearchState(
            session_id="t", topic="AI",
            draft_report="## AI Research Report\nComprehensive analysis here...",
            quality_threshold=75,
        )
        result = run_reviewer(state)
        self.assertIsNotNone(result.review_result)
        self.assertEqual(result.review_result.score, 80)
        self.assertTrue(result.review_result.approved)

    @patch("agents.reviewer.call_llm_with_retry")
    def test_reviewer_rejected(self, mock_llm):
        mock_llm.return_value = """{
            "accuracy_score": 10, "completeness_score": 8, "clarity_score": 7,
            "structure_score": 9, "depth_score": 6,
            "total_score": 40,
            "strengths": ["Topic is relevant"],
            "weaknesses": ["Lacks depth", "Missing sections", "No citations"],
            "improvement_instructions": "Completely rewrite with more detail",
            "approved": false
        }"""
        from agents.reviewer import run_reviewer
        state = ResearchState(
            session_id="t", topic="AI",
            draft_report="Short report.",
            quality_threshold=75,
        )
        result = run_reviewer(state)
        self.assertFalse(result.review_result.approved)
        self.assertEqual(result.review_result.score, 40)


class TestReportGeneration(unittest.TestCase):
    def setUp(self):
        self.report_text = """# Test Research Report

## Abstract
This is a test abstract.

## Introduction
This report tests the generation capabilities.

## Key Findings
- Finding 1: Tests pass
- Finding 2: Generation works

## Conclusion
The system is functional.

## References
1. Test Reference
"""
        self.topic = "Test Topic"
        self.session_id = "test-report-001"

    def test_markdown_generation(self):
        from utils.report_generator import save_markdown
        path = save_markdown(self.report_text, self.topic, self.session_id)
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 100)

    def test_pdf_generation(self):
        from utils.report_generator import generate_pdf
        path = generate_pdf(self.report_text, self.topic, self.session_id)
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 500)

    def test_docx_generation(self):
        from utils.report_generator import generate_docx
        path = generate_docx(self.report_text, self.topic, self.session_id)
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 1000)


class TestDatabase(unittest.TestCase):
    def test_initialize_and_stats(self):
        from database.db import initialize_db, get_app_stats
        initialize_db()
        stats = get_app_stats()
        self.assertIsNotNone(stats)
        self.assertIn("total_reports", stats)

    def test_save_and_retrieve_session(self):
        import uuid
        from database.db import save_session, get_all_sessions, delete_session, save_report, get_session_report
        sid = str(uuid.uuid4())
        save_session(sid, "Integration Test Topic", "standard", "multi_agent")
        save_report(sid, "## Test Report\nContent here.")

        sessions = get_all_sessions()
        session_ids = [s["id"] for s in sessions]
        self.assertIn(sid, session_ids)

        report = get_session_report(sid)
        self.assertIsNotNone(report)
        self.assertIn("Test Report", report)

        delete_session(sid)
        sessions_after = get_all_sessions()
        self.assertNotIn(sid, [s["id"] for s in sessions_after])


class TestWebSearch(unittest.TestCase):
    def test_format_search_results(self):
        from tools.search import format_search_results
        results = [
            {"title": "AI Article", "url": "https://example.com/ai", "snippet": "AI is transforming..."},
            {"title": "ML Paper", "url": "https://example.com/ml", "snippet": "Machine learning..."},
        ]
        formatted = format_search_results(results)
        self.assertIn("AI Article", formatted)
        self.assertIn("example.com", formatted)

    def test_empty_results(self):
        from tools.search import format_search_results
        result = format_search_results([])
        self.assertIn("No web search results", result)


if __name__ == "__main__":
    print("=" * 60)
    print("Multi-Agent Research Intelligence Platform — Test Suite")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_classes = [
        TestCommunicationBus,
        TestResearchState,
        TestPlannerAgent,
        TestFactCheckerAgent,
        TestReviewerAgent,
        TestReportGeneration,
        TestDatabase,
        TestWebSearch,
    ]

    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print()
    print(f"Tests run:    {result.testsRun}")
    print(f"Failures:     {len(result.failures)}")
    print(f"Errors:       {len(result.errors)}")

    if result.wasSuccessful():
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED")
        sys.exit(1)

