from trending_hunter.utils import normalize_url


def test_normalize_github():
    assert normalize_url("https://github.com/owner/repo") == "https://github.com/owner/repo"


def test_normalize_github_trailing_slash():
    assert normalize_url("https://github.com/owner/repo/") == "https://github.com/owner/repo"


def test_normalize_producthunt():
    assert normalize_url("https://www.producthunt.com/posts/cool-tool") == "https://producthunt.com/posts/cool-tool"


def test_normalize_producthunt_removes_query():
    assert normalize_url("https://www.producthunt.com/posts/cool-tool?ref=home") == "https://producthunt.com/posts/cool-tool"


def test_normalize_hn_item_keeps_query():
    assert normalize_url("https://news.ycombinator.com/item?id=12345") == "https://news.ycombinator.com/item?id=12345"


def test_normalize_hn_external_link():
    assert normalize_url("https://example.com/blog/post") == "https://example.com/blog/post"


def test_normalize_removes_www():
    assert normalize_url("https://www.example.com/path") == "https://example.com/path"


def test_normalize_lowercase_host():
    assert normalize_url("https://GitHub.com/owner/repo") == "https://github.com/owner/repo"


def test_normalize_removes_fragment():
    assert normalize_url("https://example.com/page#section") == "https://example.com/page"


def test_normalize_empty_url():
    assert normalize_url("") == ""


def test_cross_source_same_github_project():
    """HN linking to a GitHub repo should normalize to the same URL."""
    gh_url = "https://github.com/owner/repo"
    hn_url = "https://www.github.com/owner/repo/?ref=hackernews"
    assert normalize_url(gh_url) == normalize_url(hn_url)
