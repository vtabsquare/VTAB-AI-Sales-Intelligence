import pytest

from app.services.web_agent import extract_candidate_links, validate_public_url


def test_validate_public_url_accepts_https():
    assert validate_public_url("https://example.com/tenders") == "https://example.com/tenders"


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "http://localhost/admin",
    "http://127.0.0.1:8000/docs",
    "javascript:alert(1)",
])
def test_validate_public_url_blocks_local_or_non_web_targets(url):
    with pytest.raises(ValueError):
        validate_public_url(url)


def test_extract_candidate_links_filters_and_deduplicates():
    links = [
        {"href": "/rfp/fabric", "text": "Microsoft Fabric implementation RFP"},
        {"href": "/rfp/fabric", "text": "Duplicate Fabric link"},
        {"href": "/about", "text": "About us"},
        {"href": "https://example.com/databricks", "text": "Databricks migration partner"},
    ]
    rows = extract_candidate_links("https://example.com/procurement", links, ["microsoft fabric", "databricks"])
    assert len(rows) == 2
    assert rows[0]["url"] == "https://example.com/rfp/fabric"
    assert rows[1]["url"] == "https://example.com/databricks"
