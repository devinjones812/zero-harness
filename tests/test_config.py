from zero_harness import config


def test_auto_review_needs_a_reviewer(monkeypatch):
    assert config.reviewer() is None
    assert config.get("mode") == "ask"
    monkeypatch.setenv("TYPESAFE_API_KEY", "x")
    assert config.reviewer() == "jev"
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    assert config.reviewer() == "openai"
    assert config.get("mode") == "auto-review"


def test_chosen_reviewer_needs_its_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    config.saved["approval_provider"] = "jev"
    assert config.reviewer() is None
