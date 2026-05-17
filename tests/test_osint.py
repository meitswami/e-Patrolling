"""OSINT permalink and bio matching tests."""

from osint.bio_match import bio_similarity, username_similarity
from osint.permaliinks import build_comment_permalink, build_permalink_snapshot


def test_instagram_comment_permalink():
    url = build_comment_permalink(
        "instagram",
        username="troll1",
        post_id="ABC123",
        comment_id="cmt99",
    )
    assert url is not None
    assert "instagram.com/p/ABC123" in url


def test_twitter_status_permalink():
    url = build_comment_permalink("twitter", username="x", comment_id="12345")
    assert url == "https://twitter.com/i/status/12345"


def test_permalink_snapshot_has_deletion_note():
    snap = build_permalink_snapshot(
        platform="twitter",
        username="troll",
        post_url="https://twitter.com/user/status/1",
        comment_url=None,
        post_id="1",
        comment_id="99",
        comment_posted_at="2025-01-01T12:00:00Z",
    )
    assert snap["direct_comment_link"]
    assert "removed" in snap["deletion_note"].lower()


def test_bio_similarity_overlap():
    a = "Journalist hater | Mumbai | DM for collabs"
    b = "Mumbai based | hater of fake news journalists"
    assert bio_similarity(a, b) >= 0.2


def test_username_similarity():
    assert username_similarity("troll_99", "troll99") >= 0.9
