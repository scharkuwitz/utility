#!/usr/bin/env python3
"""Fetch documentation pages for tldr-docs. Stdlib only.

Usage: fetch.py <bundle_dir> [--no-links] <url> [<url> ...]

Saves each page as text to <bundle_dir>/src/<slug>.txt, preferring the clean
Markdown form (<url>.md) and falling back to the HTML page converted to text.
Prints, per page, a heading outline with line numbers (read only the sections you
need) and, unless --no-links, same-site links ranked by how often the page mentions
them: the candidates for the pointer pass. "have" marks pages already in src/.
"""
import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

UA = "tldr-docs/1.0 (documentation summarizer)"
LANG = re.compile(r"^[a-z]{2}(?:[-_][A-Za-z]{2})?$")  # en, en-US, pt_BR
LINK = re.compile(r"(?<!!)\[([^\]]*)\]\((https?://[^)\s]+)\)")
HEAD = re.compile(r"^(#{1,3})\s+(\S.*)$")
FENCE = ("```", "~~~")
MAX_LINKS = 30


def slug_for(url):
    """https://site/docs/en/plugins/install(.md) -> plugins-install"""
    parts = urlsplit(url)
    segs = [s for s in parts.path.split("/") if s]
    if segs:
        segs[-1] = re.sub(r"\.(md|mdx|html?|txt)$", "", segs[-1])
        if segs[-1] in ("", "index"):
            segs.pop()
    while segs and segs[0].lower() in ("docs", "doc", "documentation"):
        segs.pop(0)
    if len(segs) > 1 and LANG.match(segs[0]):
        segs.pop(0)
    s = "-".join(segs) or parts.netloc.split(":")[0]
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "index"


def canon(url):
    """Page identity: no query or fragment, no trailing slash, no .md suffix."""
    p = urlsplit(url)
    return f"{p.scheme}://{p.netloc}" + re.sub(r"\.md$", "", p.path.rstrip("/"))


# ---------- fetching ----------

def get(url):
    req = Request(url, headers={"User-Agent": UA,
                                "Accept": "text/markdown,text/plain;q=0.9,text/html;q=0.8,*/*;q=0.5"})
    with urlopen(req, timeout=30) as r:
        body = r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")
        return r.headers.get("Content-Type", ""), body


def is_html(ctype, body):
    return "html" in ctype.lower() or body.lstrip()[:100].lower().startswith(("<!doctype", "<html"))


def fetch(url):
    """Return (url_used, text). Tries <url>.md first; converts HTML when that is all there is."""
    base = url.split("#")[0].rstrip("/")
    tries = [base] if re.search(r"\.(md|txt)$", base) else [base + ".md", base]
    err = None
    for u in tries:
        try:
            ctype, body = get(u)
        except (URLError, OSError, ValueError) as e:
            err = e
            continue
        if not is_html(ctype, body):
            return u, body
        if u == tries[-1]:
            return u, html_to_text(body, u)
    raise err or RuntimeError("no usable content")


class _HtmlToText(HTMLParser):
    """Minimal HTML -> markdown-like text: headings, lists, code, links, images."""
    SKIP = {"head", "script", "style", "noscript", "svg", "nav", "footer", "aside", "form", "button", "template"}
    SKIP_ROLES = {"navigation", "banner", "contentinfo", "search", "complementary"}
    VOID = {"area", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "wbr"}
    BLOCK = {"p", "div", "section", "article", "main", "header", "ul", "ol", "table", "tr", "blockquote",
             "dl", "dt", "dd", "br", "hr", "figure", "figcaption", "details", "summary"}

    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base, self.out, self.skip, self.skip_tag, self.pre = base, [], 0, None, 0
        self.href, self.atext = None, []

    def emit(self, s):
        (self.atext if self.href is not None else self.out).append(s)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if self.skip:  # inside a skipped element: only track nesting of the same tag
            self.skip += tag == self.skip_tag
            return
        if tag not in self.VOID and (tag in self.SKIP or a.get("role") in self.SKIP_ROLES
                                     or a.get("aria-hidden") == "true"):
            self.skip, self.skip_tag = 1, tag
            return
        if re.fullmatch(r"h[1-6]", tag):
            self.emit("\n\n" + "#" * int(tag[1]) + " ")
        elif tag == "a":
            href = a.get("href") or ""
            if href and not href.startswith(("#", "javascript:", "mailto:")):
                self.href, self.atext = urljoin(self.base, href), []
        elif tag == "li":
            self.emit("\n* ")
        elif tag in ("td", "th"):
            self.emit(" | ")
        elif tag == "pre":
            self.pre += 1
            self.emit("\n```\n")
        elif tag == "code" and not self.pre:
            self.emit("`")
        elif tag == "img" and a.get("alt"):
            self.emit(f"![{a['alt']}]({urljoin(self.base, a.get('src') or '')})")
        elif tag in self.BLOCK:
            self.emit("\n")

    def handle_endtag(self, tag):
        if self.skip:
            self.skip -= tag == self.skip_tag
            return
        if tag == "a" and self.href is not None:
            text, href = "".join(self.atext).strip(), self.href
            self.href = None
            if text and text not in ("#", "¶", "§"):
                self.emit(f"[{text}]({href})")
        elif re.fullmatch(r"h[1-6]", tag):
            self.emit("\n\n")
        elif tag == "pre":
            self.pre = max(0, self.pre - 1)
            self.emit("\n```\n")
        elif tag == "code" and not self.pre:
            self.emit("`")
        elif tag in self.BLOCK:
            self.emit("\n")

    def handle_data(self, data):
        if not self.skip:
            self.emit(data if self.pre else re.sub(r"\s+", " ", data))


def html_to_text(doc, base):
    m = re.search(r"<main\b.*?</main>", doc, re.S | re.I)
    p = _HtmlToText(base)
    p.feed(m.group(0) if m else doc)
    p.close()
    text = re.sub(r"[ \t]+\n", "\n", "".join(p.out).replace("\u00b6", ""))
    text = re.sub(r"\n[ \t]+(?=[^\s])", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


# ---------- reporting ----------

def outline(lines):
    out, fenced = [], False
    for i, line in enumerate(lines, 1):
        if line.lstrip().startswith(FENCE):
            fenced = not fenced
            continue
        m = None if fenced else HEAD.match(line)
        if m:
            out.append((i, len(m.group(1)), LINK.sub(r"\1", m.group(2)).strip()))
    return out


def ranked_links(lines, page_url):
    host, me = urlsplit(page_url).netloc, canon(page_url)
    found, fenced, under = {}, False, ""
    for line in lines:
        if line.lstrip().startswith(FENCE):
            fenced = not fenced
            continue
        if fenced:
            continue
        m = HEAD.match(line)
        if m:
            under = LINK.sub(r"\1", m.group(2)).strip()
        for text, href in LINK.findall(line):
            key = canon(href)
            if urlsplit(href).netloc != host or key == me:
                continue
            e = found.setdefault(key, {"n": 0, "text": re.sub(r"[*`]", "", text).strip(), "under": under})
            e["n"] += 1
    return sorted(found.items(), key=lambda kv: -kv[1]["n"])  # stable: ties keep page order


def report(slug, used, path, text, show_links, have):
    lines = text.splitlines()
    print(f"== {slug}: {len(lines)} lines -> {path}  (from {used})")
    for i, level, h in outline(lines):
        print(f"{i:6d} {'  ' * (level - 1)}{'#' * level} {h[:90]}")
    if not show_links:
        return
    links = ranked_links(lines, used)
    print(f"  same-site links: {len(links)} (count, have, slug, url, text, [section])")
    for key, e in links[:MAX_LINKS]:
        s = slug_for(key)
        under = f"  [{e['under'][:32]}]" if e["under"] else ""
        print(f"  {e['n']:>2}x {'have' if s in have else '    '} {s:<26} {key}  \"{e['text'][:48]}\"{under}")
    if len(links) > MAX_LINKS:
        print(f"  ... {len(links) - MAX_LINKS} more")


def main():
    ap = argparse.ArgumentParser(description="Fetch docs pages into <bundle>/src/ and print outlines.")
    ap.add_argument("bundle", help="bundle directory, e.g. tldr-out/claude-code")
    ap.add_argument("urls", nargs="+", help="page URLs")
    ap.add_argument("--no-links", action="store_true", help="skip the link list (use for followed pointer pages)")
    a = ap.parse_args()
    src = Path(a.bundle) / "src"
    src.mkdir(parents=True, exist_ok=True)
    failed, seen = 0, {}
    for url in a.urls:
        slug = slug_for(url)
        if slug in seen and seen[slug] != canon(url):
            print(f"!! {url}: slug '{slug}' already used by {seen[slug]} in this run; skipped", file=sys.stderr)
            failed += 1
            continue
        try:
            used, text = fetch(url)
        except Exception as e:  # report and continue with the other pages
            print(f"!! {url}: {e}", file=sys.stderr)
            failed += 1
            continue
        seen[slug] = canon(url)
        path = src / f"{slug}.txt"
        path.write_text(text, encoding="utf-8")
        report(slug, used, path, text, not a.no_links, {p.stem for p in src.glob("*.txt")})
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
