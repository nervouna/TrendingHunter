from trending_hunter.fetchers.github import parse_trending_html

SAMPLE_HTML = """
<html><body>
<article>
  <h2><a href="/owner-a/repo-a">owner-a / repo-a</a></h2>
  <p>First test repository.</p>
  <div class="f6 text-gray mt-2">
    <span itemprop="programmingLanguage">Python</span>
    <a href="/owner-a/repo-a/stargazers">
      <svg aria-label="star"></svg>
      1,200
    </a>
    <span>500 stars today</span>
  </div>
</article>
<article>
  <h2><a href="/owner-b/repo-b">owner-b / repo-b</a></h2>
  <p>Second test repository.</p>
  <div class="f6 text-gray mt-2">
    <span itemprop="programmingLanguage">Go</span>
    <a href="/owner-b/repo-b/stargazers">
      <svg aria-label="star"></svg>
      5,000
    </a>
    <span>300 stars this week</span>
  </div>
</article>
<article>
  <h2><a href="/owner-c/repo-c">owner-c / repo-c</a></h2>
  <p>Third repo no velocity.</p>
  <div class="f6 text-gray mt-2">
    <a href="/owner-c/repo-c/stargazers">
      <svg aria-label="star"></svg>
      999
    </a>
  </div>
</article>
</body></html>
"""


def test_parse_extracts_all_repos():
    repos = parse_trending_html(SAMPLE_HTML)
    assert len(repos) == 3


def test_parse_repo_fields():
    repos = parse_trending_html(SAMPLE_HTML)
    r = repos[0]
    assert r.name == "owner-a/repo-a"
    assert r.url == "https://github.com/owner-a/repo-a"
    assert r.description == "First test repository."
    assert r.stars == 1200
    assert r.star_velocity == 500.0
    assert r.source.value == "github"


def test_parse_weekly_velocity():
    repos = parse_trending_html(SAMPLE_HTML)
    r = repos[1]
    assert r.name == "owner-b/repo-b"
    assert r.star_velocity == 300.0 / 7.0


def test_parse_no_velocity():
    repos = parse_trending_html(SAMPLE_HTML)
    r = repos[2]
    assert r.star_velocity == 0.0


def test_parse_empty_html():
    repos = parse_trending_html("<html><body></body></html>")
    assert repos == []


def test_parse_language():
    repos = parse_trending_html(SAMPLE_HTML)
    # language is not stored in Project model — it's metadata only
    # verify the parser doesn't crash on it
    assert repos[0].name == "owner-a/repo-a"


def test_parse_skips_article_without_repo_link():
    html = """<html><body>
<article>
  <p>No repo link here</p>
</article>
<article>
  <h2><a href="/owner/repo">owner / repo</a></h2>
  <p>Desc.</p>
</article>
</body></html>"""
    repos = parse_trending_html(html)
    assert len(repos) == 1
    assert repos[0].name == "owner/repo"
