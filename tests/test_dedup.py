import json
import time

from trending_hunter.dedup import SeenUrls


def test_seen_urls_initially_empty(tmp_path):
    seen = SeenUrls(tmp_path / ".seen.json")
    seen.load()
    assert not seen.is_seen("https://example.com")


def test_seen_urls_mark_and_check(tmp_path):
    seen = SeenUrls(tmp_path / ".seen.json")
    seen.mark_seen("https://example.com/a")
    assert seen.is_seen("https://example.com/a")
    assert not seen.is_seen("https://example.com/b")


def test_seen_urls_persistence(tmp_path):
    path = tmp_path / ".seen.json"
    seen = SeenUrls(path)
    seen.mark_seen("https://example.com/a")
    seen.save()

    seen2 = SeenUrls(path)
    seen2.load()
    assert seen2.is_seen("https://example.com/a")
    assert not seen2.is_seen("https://example.com/b")


def test_seen_urls_save_noop_when_clean(tmp_path):
    path = tmp_path / ".seen.json"
    seen = SeenUrls(path)
    seen.load()
    seen.save()
    assert not path.exists()


# --- Problem 2: corrupted file handling ---


def test_seen_urls_load_corrupted_file(tmp_path):
    path = tmp_path / ".seen.json"
    path.write_text("NOT VALID JSON {{{", encoding="utf-8")
    seen = SeenUrls(path)
    seen.load()
    assert not seen.is_seen("https://example.com")


def test_seen_urls_load_partial_corrupt(tmp_path):
    path = tmp_path / ".seen.json"
    path.write_text('["https://ok.com", BROKEN]', encoding="utf-8")
    seen = SeenUrls(path)
    seen.load()
    assert not seen.is_seen("https://ok.com")


# --- Problem 3: TTL support ---


def test_seen_urls_ttl_removes_old_entries(tmp_path):
    path = tmp_path / ".seen.json"
    seen = SeenUrls(path, ttl_days=1)

    # Manually write an entry with a timestamp far in the past
    old_ts = time.time() - 86400 * 10  # 10 days ago
    path.write_text(json.dumps({"https://old.com": old_ts}), encoding="utf-8")

    seen.load()
    assert not seen.is_seen("https://old.com")


def test_seen_urls_ttl_keeps_recent_entries(tmp_path):
    path = tmp_path / ".seen.json"
    seen = SeenUrls(path, ttl_days=30)

    recent_ts = time.time() - 86400 * 5  # 5 days ago
    path.write_text(json.dumps({"https://recent.com": recent_ts}), encoding="utf-8")

    seen.load()
    assert seen.is_seen("https://recent.com")


def test_seen_urls_ttl_mixed_old_and_new(tmp_path):
    path = tmp_path / ".seen.json"
    seen = SeenUrls(path, ttl_days=7)

    old_ts = time.time() - 86400 * 10  # 10 days ago
    new_ts = time.time() - 86400 * 2  # 2 days ago
    path.write_text(
        json.dumps({"https://old.com": old_ts, "https://new.com": new_ts}),
        encoding="utf-8",
    )

    seen.load()
    assert not seen.is_seen("https://old.com")
    assert seen.is_seen("https://new.com")


def test_seen_urls_backward_compat_old_list_format(tmp_path):
    path = tmp_path / ".seen.json"
    path.write_text(
        json.dumps(["https://legacy.com", "https://other.com"]), encoding="utf-8"
    )

    seen = SeenUrls(path, ttl_days=30)
    seen.load()
    # Old format entries are treated as current (no timestamp → keep them)
    assert seen.is_seen("https://legacy.com")
    assert seen.is_seen("https://other.com")


def test_seen_urls_save_stores_timestamps(tmp_path):
    path = tmp_path / ".seen.json"
    seen = SeenUrls(path, ttl_days=30)
    seen.mark_seen("https://example.com")
    seen.save()

    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "https://example.com" in data
    assert isinstance(data["https://example.com"], float)


def test_seen_urls_no_ttl_uses_flat_list(tmp_path):
    """Without ttl_days (None), storage stays as a flat list for backward compat."""
    path = tmp_path / ".seen.json"
    seen = SeenUrls(path)
    seen.mark_seen("https://example.com")
    seen.save()

    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert "https://example.com" in data


# --- Problem 4: atomic write ---


def test_seen_urls_atomic_write(tmp_path):
    path = tmp_path / ".seen.json"
    seen = SeenUrls(path)
    seen.mark_seen("https://example.com")
    seen.save()

    # No leftover temp files
    remaining = list(tmp_path.iterdir())
    assert len(remaining) == 1
    assert remaining[0].name == ".seen.json"

    # Content is valid
    seen2 = SeenUrls(path)
    seen2.load()
    assert seen2.is_seen("https://example.com")
