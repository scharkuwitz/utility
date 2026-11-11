#!/usr/bin/env python3
"""Render a tldr bundle into one self-contained HTML file. Stdlib only.

Usage: build.py <bundle_dir> [-o OUT.html]

Reads  <bundle_dir>/data/*.json    one JSON per page; optional _index.json (title, source_url, intro, order)
       <bundle_dir>/src/<slug>.txt fetched source text; every core quote is checked against it
Writes <bundle_dir>/index.html     every page of the bundle in one document, in _index.json order
Exits non-zero on schema errors. Quality problems are printed as WARN lines.
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,400;0,600;0,700;1,400'
    '&family=Source+Serif+4:opsz,wght@8..60,600&family=IBM+Plex+Mono:wght@400;500&display=swap">'
)

CSS = """
:root{--bg:#eceae4;--panel:#f8f7f3;--fg:#1d1d1b;--mut:#5c5a54;--bd:#d8d4c9;--bd2:#b9b4a6;--acc:#1d3f66;
--code:#e6e3da;--sans:"Source Sans 3",-apple-system,"Segoe UI",Roboto,Arial,sans-serif;
--serif:"Source Serif 4",Georgia,"Times New Roman",serif;--mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 var(--sans);-webkit-font-smoothing:antialiased}
main{max-width:840px;margin:0 auto;padding:28px 16px 56px}
a{color:var(--acc);text-underline-offset:2px;text-decoration-thickness:1px}
article,section{scroll-margin-top:16px}
.eyebrow{font-size:.75rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--mut)}
.pt{font:600 2rem/1.15 var(--serif);margin:4px 0 6px;letter-spacing:-.01em}
h2.pt{font-size:1.7rem}
.meta{color:var(--mut);font-size:.85rem}
.lead{font-size:1.12rem;line-height:1.5;margin:14px 0 0;max-width:68ch}
nav{display:flex;flex-wrap:wrap;gap:2px 18px;font-size:.88rem;margin:18px 0 0;padding:8px 0;border-top:1px solid var(--bd2);border-bottom:1px solid var(--bd2)}
nav span{color:var(--mut);font-weight:600}
nav a{text-decoration:none}nav a:hover{text-decoration:underline}
section{margin-top:30px}
.sh{font:600 1.3rem/1.25 var(--serif);margin:0 0 10px;display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 12px}
.sh small{font:400 .82rem var(--sans);color:var(--mut)}
.panel{background:var(--panel);border:1px solid var(--bd);border-radius:3px}
.item{padding:12px 16px}
.item+.item{border-top:1px solid var(--bd)}
.it{margin:0 0 3px;font-size:1rem;font-weight:700;display:flex;gap:10px;align-items:baseline}
.num{font:500 .78rem var(--mono);color:var(--acc);min-width:1.4em}
.body{padding-left:calc(1.4em + 10px)}
.lbl{font-size:.72rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--mut);margin-right:6px}
.why,.note{color:var(--mut);margin-top:4px;font-size:.94rem}
.row{margin-top:6px;font-size:.94rem}
ol,ul{padding-left:1.3em;margin:6px 0}
li{margin:2px 0}
ul.plain{list-style:none;padding:0;margin:0}ul.plain li.item{margin:0}
code{background:var(--code);padding:.08em .32em;border-radius:2px;font:.84em var(--mono)}
pre{background:var(--code);padding:10px 12px;overflow-x:auto;margin:8px 0;border-radius:2px;font-size:.92rem;line-height:1.45}
pre code{padding:0;background:none}
table{width:100%;border-collapse:collapse;font-size:.94rem}
td{padding:7px 16px;vertical-align:top}
tr+tr td{border-top:1px solid var(--bd)}
td:first-child{width:34%;font-weight:600}
details+details{border-top:1px solid var(--bd)}
summary{cursor:pointer;padding:9px 16px;font-weight:600;list-style:none;display:flex;gap:10px}
summary::-webkit-details-marker{display:none}
summary:before{content:"+";font:500 .95rem var(--mono);color:var(--acc);width:1em}
details[open] summary:before{content:"\\2212"}
details p{margin:0;padding:0 16px 10px calc(16px + 1em + 10px);color:var(--mut)}
.pages a{text-decoration:none;color:inherit;display:block}
.pages a:hover .it{color:var(--acc);text-decoration:underline}
.pages .note{margin-top:2px}
footer{margin-top:36px;padding-top:10px;border-top:1px solid var(--bd2);font-size:.8rem;color:var(--mut)}
figure.dg{margin:12px 0 4px;padding:12px;border:1px solid var(--bd);background:var(--bg);border-radius:2px;text-align:center}
figure.dg img,figure.dg svg{max-width:100%;height:auto}
figure.dg figcaption{font-size:.78rem;color:var(--mut);margin-top:8px}
.flow{display:flex;flex-wrap:wrap;align-items:stretch;justify-content:center;row-gap:8px}
.flow.col{flex-direction:column;align-items:center}
.fnode{border:1px solid var(--bd2);background:var(--panel);padding:5px 12px;font-size:.88rem;text-align:center;max-width:210px;border-radius:2px}
.fnode i{display:block;font-style:normal;font-size:.76rem;color:var(--mut)}
.farrow{align-self:center;color:var(--acc);padding:0 8px}
.farrow small{display:block;font-size:.7rem;color:var(--mut);text-align:center}
.flow.col .farrow{padding:2px 0}
.layers{max-width:440px;margin:0 auto;border:1px solid var(--bd2);border-radius:2px;overflow:hidden}
.layer{padding:5px 12px;font-size:.88rem;background:var(--panel)}
.layer+.layer{border-top:1px solid var(--bd2)}
.layer:first-child{background:var(--acc);color:#fff}
.layer i{font-style:normal;font-size:.76rem;opacity:.75;margin-left:.6em}
.tree,.tree ul{list-style:none;margin:0;padding-left:18px;text-align:left;font-size:.88rem}
.tree{display:inline-block;padding-left:0}
.tree li{position:relative;padding:2px 0 2px 14px;border-left:1px solid var(--bd2);margin:0}
.tree li:before{content:"";position:absolute;left:0;top:1em;width:10px;border-top:1px solid var(--bd2)}
.tree li:last-child{border-left-color:transparent}
.tree li:last-child:after{content:"";position:absolute;left:0;top:0;height:1em;border-left:1px solid var(--bd2)}
.tree>ul{padding-left:0}.tree>ul>li{border:0;padding-left:0}.tree>ul>li:before,.tree>ul>li:after{display:none}
.tree .tl{border:1px solid var(--bd2);background:var(--panel);padding:1px 8px;display:inline-block;border-radius:2px}
.tree .tl i{font-style:normal;color:var(--mut);font-size:.78rem;margin-left:.5em}
.fn{font-size:.76rem;color:var(--mut);margin:10px 0 0;padding:6px 0 0 1.4em;border-top:1px dotted var(--bd2);line-height:1.4}
.fn li{margin:1px 0}.fn a{color:var(--mut)}
sup.f{font:500 .66em var(--mono);color:var(--acc);margin-left:1px}
.layout{display:grid;grid-template-columns:200px minmax(0,840px);justify-content:center;gap:0 44px;padding:0 16px}
.layout main{margin:0;padding:28px 0 56px;max-width:none}
.layout article{margin-top:56px;padding-top:26px;border-top:2px solid var(--acc)}
.top{display:inline-block;margin-top:20px;font-size:.85rem}
.toc{position:sticky;top:0;align-self:start;max-height:100vh;overflow-y:auto;padding:30px 0 24px;font-size:.86rem;line-height:1.35}
.toc-h{display:block;font-size:.75rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);text-decoration:none;padding-bottom:8px;border-bottom:1px solid var(--bd2)}
.toc ol{list-style:none;margin:0;padding:0}
.toc li{margin:0;border-bottom:1px solid var(--bd)}
.toc a{display:flex;gap:8px;padding:7px 0;color:var(--fg);text-decoration:none}
.toc a:hover{color:var(--acc)}
@media(max-width:1080px){.layout{display:block;padding:0}.toc{display:none}.layout main{max-width:840px;margin:0 auto;padding:28px 16px 56px}}
@media(max-width:560px){.body{padding-left:0}td{display:block;width:auto!important;padding:2px 16px}tr td:first-child{padding-top:8px}tr td:last-child{padding-bottom:8px}tr+tr td+td{border-top:0}}
@media print{nav,.toc,.top{display:none}.layout{display:block}body{background:#fff}.layout article{break-before:page;border-top:0}.item,details{break-inside:avoid}}
"""

SECTIONS = (  # (JSON key, heading, hint)
    ("core", "Key concepts", "Retain these."),
    ("practice", "Exercises", "Hands-on practice."),
    ("gotchas", "Common pitfalls", ""),
    ("skip", "Lower priority", "Valid but rarely needed. Consult when required."),
    ("cheatsheet", "Quick reference", ""),
    ("recall", "Review questions", "Answer first, then expand."),
    ("sources", "Sources", ""),
)
DIAGRAM_TYPES = ("flow", "layers", "tree", "svg", "image")
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F]")
FOOTER = "<footer>Summary generated from the source documentation. Verify against the source before relying on details.</footer>"


# ---------- text helpers ----------

def esc(s):
    return html.escape(str(s), quote=False)


def attr(s):
    return html.escape(str(s), quote=True)


def inline(s):
    """Escape, then apply minimal `code` and **bold** markup."""
    t = esc(s)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)


def safe_url(u):
    u = str(u).strip()
    return u if re.match(r"^https?://", u) else "#"


def link(url, inner_html):
    return f'<a href="{attr(safe_url(url))}" rel="noopener">{inner_html}</a>'


def num(n):
    return f'<span class="num">{n:02d}</span>'


def clean_svg(svg):
    svg = re.sub(r"<script.*?</script>", "", str(svg), flags=re.S | re.I)
    svg = re.sub(r"\son\w+\s*=\s*(\"[^\"]*\"|'[^']*')", "", svg, flags=re.I)
    return re.sub(r"javascript:", "", svg, flags=re.I)


# ---------- diagrams ----------

def _node(n):
    """(label_html, note_html) for a node given as a string or {label, note}."""
    if isinstance(n, dict):
        return inline(n.get("label", "")), (inline(n["note"]) if n.get("note") else "")
    return inline(n), ""


def render_flow(dg):
    col = " col" if dg.get("direction") == "column" else ""
    arrow = "&darr;" if col else "&rarr;"
    edges = dg.get("edges") or []
    out = ""
    for i, n in enumerate(dg.get("nodes", [])):
        label, note = _node(n)
        if i:
            edge = edges[i - 1] if i - 1 < len(edges) else ""
            out += f'<div class="farrow">{arrow}' + (f"<small>{inline(edge)}</small>" if edge else "") + "</div>"
        out += f'<div class="fnode">{label}' + (f"<i>{note}</i>" if note else "") + "</div>"
    return f'<div class="flow{col}">{out}</div>'


def render_layers(dg):
    out = ""
    for n in dg.get("items", []):
        label, note = _node(n)
        out += f'<div class="layer">{label}' + (f" <i>{note}</i>" if note else "") + "</div>"
    return f'<div class="layers">{out}</div>'


def _tree(nodes):
    out = ""
    for n in nodes:
        label, note = _node(n)
        kids = _tree(n["children"]) if isinstance(n, dict) and n.get("children") else ""
        out += f'<li><span class="tl">{label}' + (f"<i>{note}</i>" if note else "") + f"</span>{kids}</li>"
    return f"<ul>{out}</ul>"


def render_diagram(dg):
    if not dg:
        return ""
    t = dg.get("type")
    if t == "flow":
        inner = render_flow(dg)
    elif t == "layers":
        inner = render_layers(dg)
    elif t == "tree":
        inner = '<div class="tree">' + _tree(dg.get("nodes", [])) + "</div>"
    elif t == "svg":
        inner = clean_svg(dg.get("svg", ""))
    elif t == "image":
        inner = (f'<img src="{attr(safe_url(dg.get("url", "")))}" alt="{attr(dg.get("alt", ""))}" '
                 'loading="lazy" referrerpolicy="no-referrer">')
    else:
        return ""
    cap = f'<figcaption>{inline(dg["caption"])}</figcaption>' if dg.get("caption") else ""
    return f'<figure class="dg">{inner}{cap}</figure>'


def diagram_size(dg):
    if not isinstance(dg, dict):
        return 0
    if dg.get("type") == "flow":
        return len(dg.get("nodes", []))
    if dg.get("type") == "layers":
        return len(dg.get("items", []))
    if dg.get("type") == "tree":
        def count(ns):
            return sum(1 + count(n.get("children", []) if isinstance(n, dict) else []) for n in ns)
        return count(dg.get("nodes", []))
    return 0


# ---------- sections ----------

def render_quotes(qs):
    out = ""
    for q in qs:
        src = f' — {link(q["url"], esc(q.get("label") or "source"))}' if q.get("url") else ""
        out += f'<li>“{inline(q["text"])}”{src}</li>'
    return f'<ol class="fn">{out}</ol>' if out else ""


def table(rows):
    return "<table>" + "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in rows) + "</table>" if rows else ""


def render_core(items, h):
    out = ""
    for n, c in enumerate(items, 1):
        qs = c.get("quotes", [])
        sup = f'<sup class="f">{",".join(map(str, range(1, len(qs) + 1)))}</sup>' if qs else ""
        out += (
            f'<div class="item"><{h} class="it">{num(n)}{inline(c["title"])}</{h}><div class="body">'
            f'<div>{inline(c.get("body", ""))}{sup}</div>'
            + (f'<div class="why"><span class="lbl">Why</span>{inline(c["why"])}</div>' if c.get("why") else "")
            + render_diagram(c.get("diagram"))
            + render_quotes(qs)
            + "</div></div>"
        )
    return out


def render_practice(items, h):
    out = ""
    for n, p in enumerate(items, 1):
        steps = "".join(f"<li>{inline(s)}</li>" for s in p.get("steps", []))
        code = p.get("code") or []
        code = code if isinstance(code, list) else [code]
        out += (
            f'<div class="item"><{h} class="it">{num(n)}{inline(p["title"])}</{h}><div class="body">'
            + (f'<div class="note">{inline(p["goal"])}</div>' if p.get("goal") else "")
            + (f"<ol>{steps}</ol>" if steps else "")
            + "".join(f'<pre><code>{esc(c.get("text", ""))}</code></pre>' for c in code)
            + (f'<div class="row"><span class="lbl">Verify</span>{inline(p["check"])}</div>' if p.get("check") else "")
            + (f'<div class="row"><span class="lbl">Variation</span>{inline(p["variation"])}</div>' if p.get("variation") else "")
            + "</div></div>"
        )
    return out


def render_sections(d, h):
    """Map of section key -> inner HTML ('' when the page has no content for it)."""
    gotchas = "".join(f'<li class="item">{inline(g)}</li>' for g in d.get("gotchas", []))
    return {
        "core": render_core(d["core"], h),
        "practice": render_practice(d.get("practice", []), h),
        "gotchas": f'<ul class="plain">{gotchas}</ul>' if gotchas else "",
        "skip": table([(link(s["url"], inline(s["title"])) if s.get("url") else inline(s["title"]),
                        inline(s.get("note", ""))) for s in d.get("skip", [])]),
        "cheatsheet": table([(inline(r["term"]), inline(r["meaning"])) for r in d.get("cheatsheet", [])]),
        "recall": "".join(f'<details><summary>{inline(r["q"])}</summary><p>{inline(r["a"])}</p></details>'
                          for r in d.get("recall", [])),
        "sources": "".join(f'<li>{link(s["url"], esc(s.get("title") or s["url"]))}</li>' for s in d.get("sources", [])),
    }


def render_article(d, slug, level, eyebrow, multi):
    """One page. level=1 when it is the whole document, 2 inside a bundle."""
    ht, hs, hi = (f"h{level + i}" for i in range(3))
    parts = render_sections(d, hi)
    navlinks = secs = ""
    for key, title, hint in SECTIONS:
        inner = parts[key]
        if not inner:
            continue
        sid = attr(f"{slug}-{key}")
        navlinks += f'<a href="#{sid}">{title}</a>'
        body = f"<ul>{inner}</ul>" if key == "sources" else f'<div class="panel">{inner}</div>'
        small = f"<small>{esc(hint)}</small>" if hint else ""
        secs += f'<section id="{sid}"><{hs} class="sh">{title} {small}</{hs}>{body}</section>'
    meta = []
    if d.get("source_url"):
        meta.append("Source: " + link(d["source_url"], esc(d["source_url"])))
    if d.get("fetched"):
        meta.append(f'Retrieved {esc(d["fetched"])}')
    if d.get("read_time_min"):
        meta.append(f'{esc(d["read_time_min"])} min read')
    return (
        f'<article id="{attr(slug)}"><div class="eyebrow">{eyebrow}</div>'
        f'<{ht} class="pt">{inline(d["title"])}</{ht}><div class="meta">{" &middot; ".join(meta)}</div>'
        f'<p class="lead">{inline(d["one_liner"])}</p>'
        f'<nav><span>{"Sections" if multi else "On this page"}</span>{navlinks}</nav>{secs}'
        + ('<a class="top" href="#contents">Back to contents</a>' if multi else "")
        + "</article>"
    )


def shell(title, body):
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{esc(title)}</title>{FONTS}<style>{CSS}</style></head><body>{body}</body></html>"
    )


def render_document(idx, pages):
    """pages: ordered list of (slug, data). One page -> plain article; several -> contents + articles."""
    if len(pages) == 1:
        slug, d = pages[0]
        return shell(d["title"], f'<main>{render_article(d, slug, 1, "Documentation summary", False)}{FOOTER}</main>')
    total = len(pages)
    title = idx.get("title") or "Documentation summaries"
    contents = side = ""
    for n, (slug, d) in enumerate(pages, 1):
        contents += (f'<a class="item" href="#{attr(slug)}"><div class="it">{num(n)}{inline(d["title"])}</div>'
                     f'<div class="body note">{inline(d["one_liner"])}</div></a>')
        side += f'<li><a href="#{attr(slug)}">{num(n)}<span>{inline(d["title"])}</span></a></li>'
    minutes = 0
    for _, d in pages:
        try:
            minutes += int(d.get("read_time_min") or 0)
        except (TypeError, ValueError):
            pass
    meta = ["Source: " + link(idx["source_url"], esc(idx["source_url"]))] if idx.get("source_url") else []
    meta += [f"{total} pages"] + ([f"{minutes} min read"] if minutes else [])
    articles = "".join(render_article(d, slug, 2, f"Part {n} of {total}", True) for n, (slug, d) in enumerate(pages, 1))
    body = (
        f'<div class="layout"><aside class="toc"><a class="toc-h" href="#contents">Contents</a><ol>{side}</ol></aside><main>'
        f'<header><div class="eyebrow">Documentation summary</div><h1 class="pt">{inline(title)}</h1>'
        f'<div class="meta">{" &middot; ".join(meta)}</div>'
        + (f'<p class="lead">{inline(idx["intro"])}</p>' if idx.get("intro") else "")
        + f'</header><section id="contents"><h2 class="sh">Contents</h2><div class="panel pages">{contents}</div></section>'
        f"{articles}{FOOTER}</main></div>"
    )
    return shell(title, body)


# ---------- checks ----------

def validate(slug, d):
    """Schema errors that would break rendering."""
    errs = []
    for k in ("title", "one_liner"):
        if not isinstance(d.get(k), str) or not d[k].strip():
            errs.append(f"{slug}: missing '{k}'")
    if not isinstance(d.get("core"), list) or not d["core"]:
        return errs + [f"{slug}: 'core' must be a non-empty list"]
    for i, c in enumerate(d["core"]):
        if not isinstance(c, dict) or "title" not in c:
            errs.append(f"{slug}: core[{i}] needs 'title'")
            continue
        qs = c.get("quotes")
        if not isinstance(qs, list) or not qs or any(not isinstance(q, dict) or not q.get("text") for q in qs):
            errs.append(f"{slug}: core[{i}] needs 'quotes' (non-empty list of {{text, url?, label?}})")
        dg = c.get("diagram")
        if dg is not None and (not isinstance(dg, dict) or dg.get("type") not in DIAGRAM_TYPES):
            errs.append(f"{slug}: core[{i}].diagram.type must be one of {'|'.join(DIAGRAM_TYPES)}")
    for key, req in (("skip", ("title",)), ("practice", ("title",)), ("cheatsheet", ("term", "meaning")),
                     ("recall", ("q", "a")), ("sources", ("url",))):
        items = d.get(key, [])
        if not isinstance(items, list):
            errs.append(f"{slug}: '{key}' must be a list")
            continue
        for i, it in enumerate(items):
            if not isinstance(it, dict) or any(r not in it for r in req):
                errs.append(f"{slug}: {key}[{i}] needs {req}")
    if not all(isinstance(g, str) for g in d.get("gotchas", [])):
        errs.append(f"{slug}: 'gotchas' must be a list of strings")
    return errs


QUOTE_CHARS = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u00a0": " "})


def norm(t):
    """Normalize for quote matching: drop markdown link syntax, blockquote markers,
    escapes and emphasis; unify quote characters, whitespace and case."""
    t = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"(?m)^[ \t]*>[ \t]?", "", t)
    t = re.sub(r"\\([^\w\s])", r"\1", t)
    t = re.sub(r"[*_`]", "", t.translate(QUOTE_CHARS))
    return re.sub(r"\s+", " ", t).strip().lower()


def strings(o, path=""):
    """Yield (path, text) for prose fields; quotes, code and svg are exempt from style checks."""
    if isinstance(o, str):
        yield path, o
    elif isinstance(o, dict):
        for k, v in o.items():
            if k not in ("quotes", "code", "svg"):
                yield from strings(v, f"{path}.{k}" if path else k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from strings(v, f"{path}[{i}]")


def lint(slug, d, src_file):
    warns = []
    src = norm(src_file.read_text(encoding="utf-8", errors="replace")) if src_file.exists() else None
    if src is None:
        warns.append(f"{slug}: no source text at {src_file}; quotes NOT verified")
    for i, c in enumerate(d["core"]):
        for q in c["quotes"]:
            t = q["text"]
            if len(t.split()) > 25:
                warns.append(f'{slug}: core[{i}] quote longer than 25 words: "{t[:50]}..."')
            if src is not None and norm(t) not in src:
                warns.append(f'{slug}: core[{i}] quote not found in source: "{t[:60]}..."')
        size = diagram_size(c.get("diagram"))
        if size > 8:
            warns.append(f"{slug}: core[{i}] diagram has {size} nodes (max 8)")
    for path, s in strings(d):
        if EMOJI.search(s):
            warns.append(f"{slug}: emoji or pictograph in {path}")
    return warns


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="Render a tldr bundle into one HTML file.")
    ap.add_argument("bundle", help="bundle directory containing data/ and src/")
    ap.add_argument("-o", "--out", help="output file (default: <bundle>/index.html)")
    a = ap.parse_args()
    root = Path(a.bundle)
    data_dir, src_dir = root / "data", root / "src"
    if not data_dir.is_dir():
        sys.exit(f"No data/ directory in {root}")

    pages, errs = {}, []
    for f in sorted(data_dir.glob("*.json")):
        if f.name == "_index.json":
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errs.append(f"{f.name}: invalid JSON ({e})")
            continue
        errs += validate(f.stem, d)
        pages[f.stem] = d
    if errs:
        sys.exit("Validation errors:\n  " + "\n  ".join(errs))
    if not pages:
        sys.exit(f"No page JSON files in {data_dir}")

    idx_file = data_dir / "_index.json"
    idx = json.loads(idx_file.read_text(encoding="utf-8")) if idx_file.exists() else {}
    listed = idx.get("order", [])
    warns = [f"_index.json: order lists unknown page '{s}'" for s in listed if s not in pages]
    order = [s for s in listed if s in pages] + sorted(s for s in pages if s not in listed)
    for slug in order:
        warns += lint(slug, pages[slug], src_dir / f"{slug}.txt")
    for w in warns:
        print("WARN", w, file=sys.stderr)

    out = Path(a.out) if a.out else root / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_document(idx, [(s, pages[s]) for s in order]), encoding="utf-8")
    note = f", {len(warns)} warning(s)" if warns else ""
    print(f"Wrote {len(pages)} page(s) into one file{note}: {out.resolve()}")


if __name__ == "__main__":
    main()
