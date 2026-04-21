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
