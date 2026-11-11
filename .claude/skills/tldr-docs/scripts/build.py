#!/usr/bin/env python3
"""Render tldr-docs content JSON into self-contained HTML pages. Stdlib only.

Usage: build.py <data_dir> <out_dir>
"""
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
.eyebrow{font-size:.75rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--mut)}
h1{font:600 2rem/1.15 var(--serif);margin:4px 0 6px;letter-spacing:-.01em}
.meta{color:var(--mut);font-size:.85rem}
.lead{font-size:1.12rem;line-height:1.5;margin:14px 0 0;max-width:68ch}
nav{display:flex;flex-wrap:wrap;gap:2px 18px;font-size:.88rem;margin:18px 0 0;padding:8px 0;border-top:1px solid var(--bd2);border-bottom:1px solid var(--bd2)}
nav span{color:var(--mut);font-weight:600}
nav a{text-decoration:none}nav a:hover{text-decoration:underline}
section{margin-top:30px}
h2{font:600 1.3rem/1.25 var(--serif);margin:0 0 10px;display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 12px}
h2 small{font:400 .82rem var(--sans);color:var(--mut)}
.panel{background:var(--panel);border:1px solid var(--bd);border-radius:3px}
.item{padding:12px 16px}
.item+.item{border-top:1px solid var(--bd)}
.item h3{margin:0 0 3px;font-size:1rem;font-weight:700;display:flex;gap:10px;align-items:baseline}
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
.pages a:hover h3{color:var(--acc);text-decoration:underline}
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
@media(max-width:560px){.body{padding-left:0}td{display:block;width:auto!important;padding:2px 16px}tr td:first-child{padding-top:8px}tr td:last-child{padding-bottom:8px}tr+tr td+td{border-top:0}}
@media print{nav{display:none}body{background:#fff}.panel{break-inside:auto}.item,details{break-inside:avoid}}
"""


def esc(s):
    return html.escape(str(s), quote=False)


def inline(s):
    """Escape, then apply minimal `code` and **bold** markup."""
    t = esc(s)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    return t


def safe_url(u):
    u = str(u).strip()
    return u if re.match(r"^https?://", u) else "#"


def clean_svg(svg):
    svg = re.sub(r"<script.*?</script>", "", str(svg), flags=re.S | re.I)
    svg = re.sub(r"\son\w+\s*=\s*(\"[^\"]*\"|'[^']*')", "", svg, flags=re.I)
    return re.sub(r"javascript:", "", svg, flags=re.I)


def _node(n):
    if isinstance(n, dict):
        note = f"<i>{inline(n['note'])}</i>" if n.get("note") else ""
        return inline(n.get("label", "")), note
    return inline(n), ""


def render_flow(dg):
    col = " col" if dg.get("direction") == "column" else ""
    arrow = "&darr;" if col else "&rarr;"
    labels = dg.get("edges") or []
    out = ""
    for i, n in enumerate(dg.get("nodes", [])):
        lab, note = _node(n)
        if i:
            el = labels[i - 1] if i - 1 < len(labels) and labels[i - 1] else ""
            out += f'<div class="farrow">{arrow}' + (f"<small>{inline(el)}</small>" if el else "") + "</div>"
        out += f'<div class="fnode">{lab}{note}</div>'
    return f'<div class="flow{col}">{out}</div>'


def render_layers(dg):
    out = ""
    for n in dg.get("items", []):
        lab, note = _node(n)
        out += f'<div class="layer">{lab}' + (f" <i>{inline(n['note'])}</i>" if note else "") + "</div>"
    return f'<div class="layers">{out}</div>'


def _tree(nodes):
    out = ""
    for n in nodes:
        lab, _ = _node(n)
        note = f"<i>{inline(n['note'])}</i>" if isinstance(n, dict) and n.get("note") else ""
        kids = _tree(n["children"]) if isinstance(n, dict) and n.get("children") else ""
        out += f'<li><span class="tl">{lab}{note}</span>{kids}</li>'
    return f"<ul>{out}</ul>"


def render_tree(dg):
    return '<div class="tree">' + _tree(dg.get("nodes", [])) + "</div>"


def render_diagram(dg):
    if not dg:
        return ""
    t = dg.get("type")
    cap = f'<figcaption>{inline(dg["caption"])}</figcaption>' if dg.get("caption") else ""
    if t == "flow":
        inner = render_flow(dg)
    elif t == "layers":
        inner = render_layers(dg)
    elif t == "tree":
        inner = render_tree(dg)
    elif t == "svg":
        inner = clean_svg(dg.get("svg", ""))
    elif t == "image":
        inner = f'<img src="{esc(safe_url(dg.get("url", "")))}" alt="{esc(dg.get("alt", ""))}" loading="lazy" referrerpolicy="no-referrer">'
    else:
        return ""
    return f'<figure class="dg">{inner}{cap}</figure>'


def render_quotes(qs):
    if not qs:
        return ""
    out = ""
    for q in qs:
        link = ""
        if q.get("url"):
            link = f' — <a href="{esc(safe_url(q["url"]))}" rel="noopener">{esc(q.get("label") or "source")}</a>'
        out += f'<li>“{inline(q["text"])}”{link}</li>'
    return f'<ol class="fn">{out}</ol>'


def page_shell(title, body, extra=""):
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{esc(title)}</title>{FONTS}<style>{CSS}</style></head>"
        f"<body><main>{body}</main>{extra}</body></html>"
    )


def code_blocks(code):
    if not code:
        return ""
    items = code if isinstance(code, list) else [code]
    out = ""
    for c in items:
        out += f'<pre><code>{esc(c.get("text", ""))}</code></pre>'
    return out


def section(sid, title, hint, inner):
    if not inner:
        return ""
    h = f"<small>{esc(hint)}</small>" if hint else ""
    return f'<section id="{sid}"><h2>{title} {h}</h2>{inner}</section>'


def panel(items):
    return f'<div class="panel">{items}</div>' if items else ""


def render_page(d, slug, has_index):
    core = ""
    for n, c in enumerate(d["core"], 1):
        nq = len(c.get("quotes", []))
        sup = f'<sup class="f">{",".join(str(i) for i in range(1, nq + 1))}</sup>' if nq else ""
        core += (
            f'<div class="item"><h3><span class="num">{n:02d}</span>{inline(c["title"])}</h3><div class="body">'
            f'<div>{inline(c.get("body", ""))}{sup}</div>'
            + (f'<div class="why"><span class="lbl">Why</span>{inline(c["why"])}</div>' if c.get("why") else "")
            + render_diagram(c.get("diagram"))
            + render_quotes(c.get("quotes"))
            + "</div></div>"
        )
    skip = ""
    if d.get("skip"):
        skip = "<table>" + "".join(
            f'<tr><td>{inline(s["title"])}</td><td>{inline(s.get("note", ""))}</td></tr>' for s in d["skip"]
        ) + "</table>"
    practice = ""
    for i, p in enumerate(d.get("practice", []), 1):
        steps = "".join(f"<li>{inline(s)}</li>" for s in p.get("steps", []))
        practice += (
            f'<div class="item"><h3><span class="num">{i:02d}</span>{inline(p["title"])}</h3><div class="body">'
            + (f'<div class="note">{inline(p["goal"])}</div>' if p.get("goal") else "")
            + (f"<ol>{steps}</ol>" if steps else "")
            + code_blocks(p.get("code"))
            + (f'<div class="row"><span class="lbl">Verify</span>{inline(p["check"])}</div>' if p.get("check") else "")
            + (f'<div class="row"><span class="lbl">Variation</span>{inline(p["variation"])}</div>' if p.get("variation") else "")
            + "</div></div>"
        )
    gotchas = "".join(f'<li class="item">{inline(g)}</li>' for g in d.get("gotchas", []))
    gotchas = f'<ul class="plain">{gotchas}</ul>' if gotchas else ""
    cheat = ""
    if d.get("cheatsheet"):
        cheat = "<table>" + "".join(
            f'<tr><td>{inline(r["term"])}</td><td>{inline(r["meaning"])}</td></tr>' for r in d["cheatsheet"]
        ) + "</table>"
    recall = "".join(
        f'<details><summary>{inline(r["q"])}</summary><p>{inline(r["a"])}</p></details>' for r in d.get("recall", [])
    )
    sources = ""
    if d.get("sources"):
        sources = "<ul>" + "".join(
            f'<li><a href="{esc(safe_url(s["url"]))}" rel="noopener">{esc(s.get("title") or s["url"])}</a></li>'
            for s in d["sources"]
        ) + "</ul>"

    parts = [
        ("core", "Key concepts", "Retain these.", panel(core)),
        ("practice", "Exercises", "Hands-on practice.", panel(practice)),
        ("gotchas", "Common pitfalls", "", panel(gotchas)),
        ("skip", "Lower priority", "Valid but rarely needed. Consult when required.", panel(skip)),
        ("cheat", "Quick reference", "", panel(cheat)),
        ("recall", "Review questions", "Answer first, then expand.", panel(recall)),
        ("sources", "Sources", "", sources),
    ]
    nav = "".join(f'<a href="#{i}">{t}</a>' for i, t, _, c in parts if c)
    if has_index:
        nav = '<a href="index.html">All pages</a>' + nav
    meta = []
    if d.get("source_url"):
        meta.append(f'Source: <a href="{esc(safe_url(d["source_url"]))}" rel="noopener">{esc(d["source_url"])}</a>')
    if d.get("fetched"):
        meta.append(f'Retrieved {esc(d["fetched"])}')
    if d.get("read_time_min"):
        meta.append(f'{esc(d["read_time_min"])} min read')
    body = (
        '<div class="eyebrow">Documentation summary</div>'
        f'<h1>{inline(d["title"])}</h1><div class="meta">{" &middot; ".join(meta)}</div>'
        f'<p class="lead">{inline(d["one_liner"])}</p><nav><span>On this page</span>{nav}</nav>'
        + "".join(section(i, t, h, c) for i, t, h, c in parts)
        + "<footer>Summary generated from the source documentation. Verify against the source before relying on details.</footer>"
    )
    return page_shell(d["title"], body)


def render_index(idx, pages):
    items = ""
    for n, (slug, d) in enumerate(pages, 1):
        items += (
            f'<a class="item" href="{esc(slug)}.html"><h3><span class="num">{n:02d}</span>{inline(d["title"])}</h3>'
            f'<div class="body note">{inline(d["one_liner"])}</div></a>'
        )
    meta = (
        f'<div class="meta">Source: <a href="{esc(safe_url(idx["source_url"]))}" rel="noopener">{esc(idx["source_url"])}</a></div>'
        if idx.get("source_url") else ""
    )
    body = (
        f'<div class="eyebrow">Documentation summary</div><h1>{inline(idx.get("title", "TLDR"))}</h1>{meta}'
        + (f'<p class="lead">{inline(idx["intro"])}</p>' if idx.get("intro") else "")
        + f'<section><div class="panel pages">{items}</div></section>'
    )
    return page_shell(idx.get("title", "TLDR"), body)


def validate(slug, d):
    errs = []
    for k in ("title", "one_liner"):
        if not isinstance(d.get(k), str) or not d[k].strip():
            errs.append(f"{slug}: missing '{k}'")
    if not isinstance(d.get("core"), list) or not d.get("core"):
        errs.append(f"{slug}: 'core' must be a non-empty list")
    else:
        for i, c in enumerate(d["core"]):
            if not isinstance(c, dict) or "title" not in c:
                errs.append(f"{slug}: core[{i}] needs 'title'")
                continue
            qs = c.get("quotes")
            if not isinstance(qs, list) or not qs or any(not isinstance(q, dict) or not q.get("text") for q in qs):
                errs.append(f"{slug}: core[{i}] needs 'quotes' (non-empty list of {{text, url?}}) supporting its claims")
            dg = c.get("diagram")
            if dg is not None and (not isinstance(dg, dict) or dg.get("type") not in ("flow", "layers", "tree", "svg", "image")):
                errs.append(f"{slug}: core[{i}].diagram.type must be flow|layers|tree|svg|image")
    for key, req in (("skip", ("title",)), ("practice", ("title",)), ("cheatsheet", ("term", "meaning")),
                     ("recall", ("q", "a")), ("sources", ("url",))):
        for i, it in enumerate(d.get(key, []) or []):
            if not isinstance(it, dict) or any(r not in it for r in req):
                errs.append(f"{slug}: {key}[{i}] needs {req}")
    return errs


def norm(t):
    t = t.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    t = re.sub(r"[*_`]", "", t)
    return re.sub(r"\s+", " ", t).strip().lower()


def check_quotes(slug, d, src_dir):
    """Warn when a quote is not found verbatim in the saved source text."""
    f = src_dir / f"{slug}.txt"
    if not f.exists():
        return [f"{slug}: no source text at {f}; quotes NOT verified"]
    src = norm(f.read_text(encoding="utf-8", errors="replace"))
    warns = []
    for i, c in enumerate(d["core"]):
        for q in c.get("quotes", []):
            if norm(q["text"]) not in src:
                warns.append(f'{slug}: core[{i}] quote not found in source: "{q["text"][:60]}..."')
    return warns


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    data_dir, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
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

    src_dir = data_dir.parent / "src"
    warns = [w for slug, d in pages.items() for w in check_quotes(slug, d, src_dir)]
    for w in warns:
        print("WARN", w, file=sys.stderr)

    multi = len(pages) > 1
    for slug, d in pages.items():
        (out_dir / f"{slug}.html").write_text(render_page(d, slug, multi), encoding="utf-8")
    entry = out_dir / f"{next(iter(pages))}.html"
    if multi:
        idx_file = data_dir / "_index.json"
        idx = json.loads(idx_file.read_text(encoding="utf-8")) if idx_file.exists() else {}
        order = [s for s in idx.get("order", []) if s in pages] + sorted(s for s in pages if s not in idx.get("order", []))
        (out_dir / "index.html").write_text(render_index(idx, [(s, pages[s]) for s in order]), encoding="utf-8")
        entry = out_dir / "index.html"
    print(f"Wrote {len(pages)} page(s). Open: {entry.resolve()}")


if __name__ == "__main__":
    main()
