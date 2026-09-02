'''
Unit tests for Google Form Filler and LinkedIn Posts Scraper.
'''

import os
import pytest
from unittest.mock import MagicMock

from modules.google_form_filler import (
    GoogleFormFiller,
    ensure_history_file,
    is_form_already_applied,
    log_form_application
)
from modules.linkedin_posts_scraper import LinkedInPostsScraper, GOOGLE_FORM_REGEX


class _MockMsg:
    def __init__(self, content):
        self.content = content


class _MockAIModel:
    def __init__(self, reply):
        self.reply = reply

    def invoke(self, messages):
        return _MockMsg(self.reply)


class _MockAIClient:
    def __init__(self, reply):
        self.model = _MockAIModel(reply)


def test_deterministic_answer_matching():
    mock_driver = MagicMock()
    filler = GoogleFormFiller(driver=mock_driver, ai_client=None)

    # Test names
    assert filler.get_deterministic_answer("Full Name *") == "Pulkit Khanna"
    assert filler.get_deterministic_answer("First Name") == "Pulkit"
    assert filler.get_deterministic_answer("Last Name") == "Khanna"

    # Test contact
    assert filler.get_deterministic_answer("Email Address") == "pulkitkhanna1@gmail.com"
    assert filler.get_deterministic_answer("Mobile / Phone Number *") == "7042680055"

    # Test social links
    assert "linkedin.com/in/pulkit-khanna" in filler.get_deterministic_answer("LinkedIn Profile URL")
    assert "github.com/pulkitkhanna1" in filler.get_deterministic_answer("GitHub / Portfolio link")

    # Test professional details
    assert filler.get_deterministic_answer("Years of experience") == "2"
    assert filler.get_deterministic_answer("Current Company") == "Pocket FM"
    assert filler.get_deterministic_answer("Notice Period") == "30 days"
    assert filler.get_deterministic_answer("Current CTC") == "1800000"
    assert filler.get_deterministic_answer("Expected CTC") == "2500000"


def test_ai_answer_generation():
    mock_driver = MagicMock()
    stub_client = _MockAIClient("I have managed growth experiments and $1.5M monthly ad spend.")
    filler = GoogleFormFiller(driver=mock_driver, ai_client=stub_client)

    ans = filler.ask_ai("Why are you a good fit for this role?")
    assert "managed growth experiments" in ans


def test_google_form_url_regex():
    mock_driver = MagicMock()
    scraper = LinkedInPostsScraper(driver=mock_driver)

    sample_post = """
    We are hiring Growth Managers!
    Please fill this form: https://forms.gle/abc123XYZ456
    Or apply via https://docs.google.com/forms/d/e/1FAIpQLSc987654321/viewform?usp=sf_link
    """

    urls = scraper.extract_forms_from_text(sample_post)
    assert len(urls) == 2
    assert "https://forms.gle/abc123XYZ456" in urls
    assert "https://docs.google.com/forms/d/e/1FAIpQLSc987654321/viewform?usp=sf_link" in urls


def test_history_logging_and_deduplication(tmp_path, monkeypatch):
    test_csv = str(tmp_path / "test_applied.csv")
    monkeypatch.setattr("modules.google_form_filler.HISTORY_FILE", test_csv)

    ensure_history_file()
    assert os.path.exists(test_csv)

    test_url = "https://forms.gle/sampleform123"
    assert not is_form_already_applied(test_url)

    log_form_application(test_url, "Growth Manager Role", "Applied", "Test note")
    assert is_form_already_applied(test_url)
    assert is_form_already_applied(test_url + "?usp=sf_link")
