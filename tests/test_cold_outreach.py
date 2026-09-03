'''
Unit tests for ColdMessageGenerator and LinkedInOutreach modules.
'''

import os
import pytest
from unittest.mock import MagicMock

from modules.cold_message_generator import ColdMessageGenerator
from modules.linkedin_outreach import (
    LinkedInOutreach,
    ensure_outreach_history_file,
    is_recruiter_already_contacted,
    log_recruiter_outreach
)


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


def test_fallback_connection_note_length():
    generator = ColdMessageGenerator(use_ai=False)
    note = generator.generate_connection_note(
        recruiter_name="Sarah Jenkins",
        recruiter_title="Lead Tech Recruiter",
        company="Stripe",
        target_role="Program Manager"
    )

    # Must be strictly under LinkedIn's 300 character limit
    assert len(note) <= 300
    assert "Sarah" in note
    assert "Stripe" in note
    assert "Pulkit" in note


def test_ai_connection_note_character_constraint():
    long_reply = "<think>Some inner reasoning thoughts here\nMore thoughts</think>\nHi John, I am a Program & Growth Manager at Pocket FM who scaled ARR to $120M. Would love to connect regarding Google opportunities! - Pulkit"
    stub_client = _MockAIClient(long_reply)
    generator = ColdMessageGenerator(ai_client=stub_client, use_ai=True)

    note = generator.generate_connection_note(
        recruiter_name="John Doe",
        company="Google"
    )
    # Must be stripped of think tags and under 300 chars
    assert "<think>" not in note
    assert "John" in note
    assert len(note) <= 300


def test_direct_message_generation():
    generator = ColdMessageGenerator(use_ai=False)
    msg = generator.generate_direct_message(
        recruiter_name="Alex Rivera",
        company="Uber",
        target_role="Growth Manager"
    )

    assert "Alex" in msg
    assert "Uber" in msg
    assert "80M" in msg or "120M" in msg
    assert "Pocket FM" in msg


def test_recruiter_history_and_deduplication(tmp_path, monkeypatch):
    test_csv = str(tmp_path / "test_outreach.csv")
    monkeypatch.setattr("modules.linkedin_outreach.OUTREACH_HISTORY_FILE", test_csv)

    ensure_outreach_history_file()
    assert os.path.exists(test_csv)

    sample_url = "https://www.linkedin.com/in/recruiter-jane-doe"
    assert not is_recruiter_already_contacted(sample_url)

    log_recruiter_outreach(
        profile_url=sample_url,
        name="Jane Doe",
        company="Amazon",
        role="Product Recruiter",
        msg_type="Connection Note",
        message="Hi Jane, would love to connect!",
        status="Sent"
    )

    assert is_recruiter_already_contacted(sample_url)
    assert is_recruiter_already_contacted(sample_url + "/?miniProfileUrn=...")


def test_email_draft_generation():
    generator = ColdMessageGenerator(use_ai=False)
    subject, body = generator.generate_email_draft(
        recruiter_name="Muskan Khandelwal",
        company="upGrad",
        target_role="Program Manager"
    )

    assert "Application & Interest" in subject
    assert "Program Manager" in subject
    assert "upGrad" in subject
    assert "Pulkit Khanna" in subject
    assert "Muskan" in body
    assert "Pocket FM" in body


def test_recruiter_email_logging(tmp_path, monkeypatch):
    from modules.linkedin_outreach import log_recruiter_email, EMAIL_OUTREACH_FILE
    test_email_csv = str(tmp_path / "test_emails.csv")
    monkeypatch.setattr("modules.linkedin_outreach.EMAIL_OUTREACH_FILE", test_email_csv)

    log_recruiter_email(
        name="Muskan Khandelwal",
        company="upGrad",
        role="Program Manager",
        email="muskan@upgrad.com",
        subject="Application & Interest",
        body="Hi Muskan, ...",
        profile_url="https://www.linkedin.com/in/muskan-khandelwal",
        status="Drafted"
    )

    assert os.path.exists(test_email_csv)
    with open(test_email_csv, "r", encoding="utf-8") as f:
        content = f.read()
        assert "muskan@upgrad.com" in content
        assert "upGrad" in content
        assert "Program Manager" in content
