from patchly.actions import ActionResult
from patchly.risk import score_issue, classify, action_for_score, risk_context


def test_score_low():
    issue = ActionResult("test", "info", "minor formatting issue")
    assert score_issue(issue) <= 1


def test_score_medium():
    issue = ActionResult("test", "warning", "auth token handling issue")
    score = score_issue(issue)
    assert score >= 1


def test_score_high():
    issue = ActionResult("test", "error", "security vulnerability in auth password system")
    score = score_issue(issue)
    assert score >= 2


def test_classify_low():
    assert classify(0) == "low"
    assert classify(1) == "low"


def test_classify_medium():
    assert classify(2) == "medium"
    assert classify(3) == "medium"


def test_classify_high():
    assert classify(4) == "high"


def test_action_for_score():
    assert action_for_score(0) == "comment"
    assert action_for_score(2) == "pr"
    assert action_for_score(4) == "review_required"


def test_risk_context_empty():
    ctx = risk_context([], "no issues")
    assert "score=0" in ctx


def test_risk_context_with_issues():
    ctx = risk_context(["auth.py"], "security issue found")
    assert "score=" in ctx
