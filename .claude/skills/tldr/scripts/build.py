#!/usr/bin/env python3
"""Render a tldr bundle into one self-contained HTML document. Stdlib only.

Usage: build.py <bundle_dir> [-o OUT.html]

Reads   <bundle>/pages/*.md   page sources (syntax: references/format.md); pages/index.md is the start page
        <bundle>/src/         fetched sources and src/_sources.json; quoted citations are checked against them
        <skill>/assets/       style.css and app.js, inlined into the output
Writes  <bundle>/index.html   every page in one file, shown one page at a time
Prints  ERROR (exit status 1: broken syntax or references), WARN (quality problems to fix before
        handing the document over), NOTE (information only), then a one-line summary.
"""
import argparse
import datetime as dt
import html
import json
import math
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

ASSETS = Path(__file__).resolve().parent.parent / "assets"
FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500'
    '&family=IBM+Plex+Sans:ital,wght@0,400;0,600;1,400&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600'
    '&display=swap">'
)

CALLOUTS = {"note": "Note", "tip": "Tip", "warning": "Warning"}
HATNOTES = {"main": "Main article: ", "see": "See also: ", "hatnote": ""}
CONTAINERS = set(CALLOUTS) | {"background", "infobox", "example", "recipes", "exercise", "recall", "pages"}
DIAGRAM_LIMITS = {"flow": 8, "sequence": 12, "stack": 8, "tree": 30, "nest": 12, "svg": 0}
MAX_QUOTE_WORDS = 30
MAX_RECIPES = 8
MAX_LEAD_WORDS = 160
LONG_PAGE_MIN = 20
WPM = 220
UNCITED_OK = re.compile(r"(?i)check yourself|not covered|further reading|glossary|terms|see also|exercise|practice|try it|recipes")
SEP = " \u00b7 "
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F]")

FENCE = re.compile(r"^( {0,3})(`{3,}|~{3,})\s*(.*)$")
DIRECTIVE = re.compile(r"^:::\s*([A-Za-z][\w-]*)\s*(.*)$")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
FOOTDEF = re.compile(r"^\[\^([^\]\s]+)\]:\s*(.*)$")
LIST = re.compile(r"^( {0,3})([-*+]|\d{1,3}[.)])(\s+)(.*)$")
TABLE_SEP = re.compile(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?$")
IMAGE = re.compile(r'^!\[([^\]]*)\]\(\s*(\S+?)(?:\s+"([^"]*)")?\s*\)$')
HR = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")
PH = re.compile(r"\{\{(.+?)\}\}")
NOTE_QUOTE = re.compile(r'^[“"](?P<q>.+)[”"]\s+(?P<u>https?://\S+?)(?:\s+\((?P<l>[^)]*)\))?\s*$', re.S)
NOTE_URL = re.compile(r"^(?P<u>https?://\S+?)(?:\s+\((?P<l>[^)]*)\))?\s*$")
INLINE = re.compile(r"""
  (?P<code>(?P<tk>`+)(?P<ct>.+?)(?P=tk))
| (?P<fn>\[\^(?P<fk>[^\]\s]+)\])
| (?P<img>!\[(?P<ia>[^\]]*)\]\((?P<iu>[^)\s]+)\))
| (?P<link>\[(?P<lt>(?:[^\[\]]|\[[^\[\]]*\])+)\]\((?P<lu>[^()\s]+(?:\([^()\s]*\)[^()\s]*)*)(?:\s+"(?P<ltitle>[^"]*)")?\))
| (?P<auto><(?P<au>https?://[^\s<>]+)>)
| (?P<strong>\*\*(?=\S)(?P<st>.+?)(?<=\S)\*\*)
| (?P<em>(?<![\w*\\])\*(?=[^\s*])(?P<et>.+?)(?<=[^\s*\\])\*(?![\w*]))
| (?P<em2>(?<![\w\\])_(?=\S)(?P<e2t>.+?)(?<=\S)_(?!\w))
| (?P<esc>\\(?P<ec>[\\`*_{}\[\]()#+\-.!|<>~]))
""", re.X | re.S)

HASH_LANGS = {"sh", "bash", "shell", "zsh", "fish", "console", "python", "py", "yaml", "yml", "toml", "ruby",
              "rb", "r", "perl", "make", "makefile", "dockerfile", "conf", "ini", "gitignore", "nginx", "hcl",
              "terraform", "tf", "powershell", "ps1", "elixir", "ex", "julia", "nix", "cmake", "env", "dotenv"}
SLASH_LANGS = {"js", "javascript", "mjs", "cjs", "ts", "typescript", "jsx", "tsx", "go", "rust", "rs", "c", "h",
               "cpp", "c++", "cc", "java", "kotlin", "kt", "swift", "jsonc", "json5", "css", "scss", "less",
               "php", "cs", "csharp", "dart", "scala", "groovy", "gradle", "proto", "zig", "solidity", "graphql"}
DASH_LANGS = {"sql", "lua", "haskell", "hs", "elm", "ada"}
TAG_LANGS = {"html", "xml", "svg", "vue", "svelte"}
SHELL_LANGS = {"sh", "bash", "shell", "zsh", "fish", "console", "shell-session", "powershell", "ps1", ""}
KEY_LANGS = {"yaml", "yml", "toml", "ini", "conf", "env", "dotenv"}
JSON_LANGS = {"json", "jsonc", "json5"}
TRANSLATE = {0x2018: "'", 0x2019: "'", 0x201C: '"', 0x201D: '"', 0x2013: "-", 0x2014: "-", 0x00A0: " ",
             0x2026: "..."}


# ---------- log ----------

class Log:
    def __init__(self):
        self.items = []

    def add(self, level, where, msg):
        self.items.append((level, where, msg))

    def count(self, level):
        return sum(1 for item in self.items if item[0] == level)


LOG = Log()


# ---------- small helpers ----------

def esc(s):
    return html.escape(s, quote=False)


def attr(s):
    return html.escape(s, quote=True)


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def words(s):
    return len(re.findall(r"\S+", s))


def slugify(text):
    t = html.unescape(re.sub(r"<[^>]+>", "", text)).strip().lower()
    t = re.sub(r"[^\w\- ]+", "", t)
    return re.sub(r"\s+", "-", t).strip("-") or "section"


def canon(url):
    p = urlsplit(url.strip())
    return p.netloc.lower() + re.sub(r"\.md$", "", p.path.rstrip("/"))


def norm(s):
    """Normalize text for quote matching: markup, quotes, dashes and whitespace don't count."""
    s = html.unescape(s).translate(TRANSLATE)
    s = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"(?m)^[ \t]*(?:>[ \t]?)+", "", s)
    s = re.sub(r"\\(.)", r"\1", s)
    s = re.sub(r"[*_`]", "", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def plain(s):
    return re.sub(r"[`*_]", "", s).strip()


def smart(s, prev=" "):
    """Curly quotes and ellipses for prose; `prev` is the character before this run of text."""
    out = []
    for k, ch in enumerate(s):
        p = s[k - 1] if k else prev
        opening = p.isspace() or p in "([{—–/-"
        if ch == '"':
            out.append("“" if opening else "”")
        elif ch == "'":
            out.append("‘" if opening else "’")
        else:
            out.append(ch)
    return esc("".join(out).replace("...", "…"))


def nice_date(s):
    try:
        d = dt.date.fromisoformat(s)
        return f"{d.day} {d.strftime('%B')} {d.year}"
    except (TypeError, ValueError):
        return s or ""


def short_url(url):
    p = urlsplit(url)
    return (p.netloc + p.path).rstrip("/")


def split_note(s):
    label, _, note = s.partition(" : ")
    return label.strip(), note.strip() or None


def front_matter(raw):
    lines = raw.splitlines()
    meta = {}
    if lines and lines[0].strip() == "---":
        for j in range(1, len(lines)):
            if lines[j].strip() == "---":
                for line in lines[1:j]:
                    key, sep, value = line.partition(":")
                    if sep and key.strip() and not line.startswith((" ", "\t", "#")):
                        value = value.strip()
                        if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
                            value = value[1:-1]
                        meta[key.strip().lower()] = value
                return meta, lines[j + 1:], j + 2
    return meta, lines, 1


def dedent(lines, n):
    """Remove up to n leading spaces from each line (the indentation of the opening fence)."""
    return [l[min(n, len(l) - len(l.lstrip(" "))):] for l in lines]


def fence_end(lines, i, marker):
    for j in range(i + 1, len(lines)):
        t = lines[j].strip()
        if t.startswith(marker) and set(t) == {marker[0]}:
            return j
    return None


def directive_end(lines, i):
    depth, fence = 0, None
    for j in range(i + 1, len(lines)):
        t = lines[j].strip()
        if fence:
            if t.startswith(fence) and set(t) == {fence[0]}:
                fence = None
            continue
        m = FENCE.match(lines[j])
        if m:
            fence = m.group(2)
            continue
        if t == ":::":
            if depth == 0:
                return j
            depth -= 1
        else:
            d = DIRECTIVE.match(t)
            if d and d.group(1).lower() not in HATNOTES:
                depth += 1
    return None


def sanitize_svg(s):
    s = re.sub(r"(?is)<(script|foreignObject|iframe)\b.*?</\1\s*>", "", s)
    s = re.sub(r"(?i)\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", s)
    s = re.sub(r"(?i)((?:xlink:)?href\s*=\s*[\"'])\s*javascript:[^\"']*", r"\1#", s)
    return s.strip()


# ---------- code highlighting (deliberately small: comments, keys, prompts, placeholders) ----------

def comment_start(line, lang):
    if lang in HASH_LANGS:
        marks = ("#",)
    elif lang in SLASH_LANGS:
        marks = ("//", "/*")
    elif lang in DASH_LANGS:
        marks = ("--",)
    elif lang in TAG_LANGS:
        marks = ("<!--",)
    else:
        return None
    quote = None
    for k, ch in enumerate(line):
        if quote:
            if ch == quote and line[k - 1] != "\\":
                quote = None
            continue
        if ch in "\"`" or (ch == "'" and lang not in KEY_LANGS):
            quote = ch
            continue
        for mark in marks:
            if line.startswith(mark, k):
                if mark == "#" and k and not line[k - 1].isspace():
                    break
                if mark == "//" and k and line[k - 1] == ":":
                    break
                return k
    return None


def hl_line(line, lang, ph):
    cut = comment_start(line, lang)
    code, com = (line[:cut], line[cut:]) if cut is not None else (line, "")
    e = esc(code)
    if lang in KEY_LANGS:
        e = re.sub(r"^(\s*(?:-\s+)?)([A-Za-z_][\w.\-]*|\"[^\"]*\")(?=\s*[:=](?:\s|$))", r'\1<span class="k">\2</span>', e)
    elif lang in JSON_LANGS:
        e = re.sub(r"(\"(?:[^\"\\]|\\.)*\")(?=\s*:)", r'<span class="k">\1</span>', e)
    if ph:
        e = PH.sub(r"<var>\1</var>", e)
    if com:
        e += f'<span class="c">{esc(com)}</span>'
    return e


def highlight(code, lang, ph=False):
    lines = code.split("\n")
    session = lang in SHELL_LANGS and any(l.startswith("$ ") for l in lines)
    front, cont, out = False, False, []
    for idx, line in enumerate(lines):
        if lang == "diff":
            cls = ("ins" if line.startswith("+") and not line.startswith("+++")
                   else "del" if line.startswith("-") and not line.startswith("---") else "")
            out.append(f'<span class="{cls}">{esc(line)}</span>' if cls else esc(line))
        elif lang in ("md", "markdown", "mdx"):
            if idx == 0 and line.strip() == "---":
                front = True
                out.append(esc(line))
            elif front:
                front = line.strip() != "---"
                out.append(hl_line(line, "yaml", ph) if front else esc(line))
            else:
                out.append(hl_line(line, "html", ph))
        elif session:
            if line.startswith("$ ") or cont:
                body = line[2:] if line.startswith("$ ") and not cont else line
                prompt = '<span class="p">$ </span>' if line.startswith("$ ") and not cont else ""
                out.append(prompt + hl_line(body, "bash", ph))
                cont = line.rstrip().endswith("\\")
            else:
                out.append(f'<span class="o">{esc(line)}</span>')
        else:
            out.append(hl_line(line, lang, ph))
    return "\n".join(out)


# ---------- sources (for quote checks and citation labels) ----------

class Sources:
    def __init__(self, src):
        self.meta, self.raw, self.norm, self.by_url, self.heads = {}, {}, {}, {}, {}
        manifest = src / "_sources.json"
        if manifest.is_file():
            try:
                self.meta = json.loads(manifest.read_text(encoding="utf-8"))
            except ValueError:
                LOG.add("WARN", "src/_sources.json", "unreadable; citation labels fall back to URLs")
        if src.is_dir():
            for p in sorted(src.glob("*.md")):
                text = p.read_text(encoding="utf-8", errors="replace")
                self.raw[p.stem], self.norm[p.stem] = text, norm(text)
        for slug, m in self.meta.items():
            for u in (m.get("url"), m.get("used")):
                if u:
                    self.by_url[canon(u)] = slug

    def slug_for(self, url):
        return self.by_url.get(canon(url)) if url else None

    def contains(self, quote, url):
        """True or False, or None when there is nothing fetched to check against."""
        if not self.norm:
            return None
        parts = [norm(p) for p in re.split(r"\s*(?:\.\.\.|…)\s*", quote)]
        parts = [p for p in parts if p]
        slug = self.slug_for(url)
        pool = [self.norm[slug]] if slug in self.norm else list(self.norm.values())
        for text in pool:
            pos, ok = 0, True
            for part in parts:
                k = text.find(part, pos)
                if k < 0:
                    ok = False
                    break
                pos = k + len(part)
            if ok:
                return True
        return False

    def title(self, url):
        slug = self.slug_for(url)
        return self.meta.get(slug, {}).get("title") if slug else None

    def label(self, url):
        slug = self.slug_for(url)
        frag = urlsplit(url).fragment
        section = None
        if frag and slug in self.raw:
            if slug not in self.heads:
                found, fenced = {}, False
                for line in self.raw[slug].splitlines():
                    if line.lstrip().startswith(("```", "~~~")):
                        fenced = not fenced
                        continue
                    m = None if fenced else re.match(r"^#{1,6}\s+(.+?)\s*#*$", line)
                    if m:
                        text = plain(re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", m.group(1)))
                        found.setdefault(slugify(text), text)
                self.heads[slug] = found
            section = self.heads[slug].get(frag.lower())
        if frag and not section:
            section = frag.replace("-", " ")
        title = self.title(url) or short_url(url)
        return title + (f" § {section}" if section else "")


# ---------- page ----------

class Page:
    def __init__(self, path, bundle):
        self.bundle, self.slug = bundle, path.stem
        self.where = f"pages/{path.name}"
        self.is_start = self.slug == "index"
        self.id = "start" if self.is_start else self.slug
        raw = path.read_text(encoding="utf-8")
        self.meta, body, first = front_matter(raw)
        self.title = self.meta.get("title", "")
        if not self.title:
            self.log("ERROR", 1, "front matter needs a title (--- / title: ... / ---)")
            self.title = self.slug
        self.heads, self.ids, self.sections, self.internal = [], set(), [], []
        self.notes, self.uses, self.num, self.parsed = {}, {}, {}, {}
        self.figures = self.code_words = self.code_blocks = 0
        self.infobox = None
        self.has = {"recall": 0, "practice": 0, "background": 0}
        self.verified = self.quotes = 0
        fenced = None
        for i, line in enumerate(raw.splitlines(), 1):
            m = FENCE.match(line)
            if m and (fenced is None or (m.group(2).startswith(fenced) and not m.group(3))):
                fenced = None if fenced else m.group(2)
                continue
            if not fenced and EMOJI.search(re.sub(r"(`+).+?\1", "", line)):
                self.log("WARN", i, "emoji or pictograph in prose; use words (Yes/No, Note, Warning)")
        self.body = "\n".join(self.blocks(body, first, top=True))

    def log(self, level, line, msg):
        LOG.add(level, f"{self.where}:{line}" if line else self.where, msg)

    def unique_id(self, base):
        hid, k = f"{self.id}--{base}", 2
        while hid in self.ids:
            hid, k = f"{self.id}--{base}-{k}", k + 1
        self.ids.add(hid)
        return hid

    # ----- blocks -----

    def interrupts(self, line):
        s = line.strip()
        return bool(FENCE.match(line) or DIRECTIVE.match(s) or s == ":::" or HEADING.match(s)
                    or FOOTDEF.match(s) or LIST.match(line) or s.startswith((">", "|")) or IMAGE.match(s))

    def blocks(self, lines, ln0, top=False):
        out, i, n = [], 0, len(lines)
        while i < n:
            line = lines[i]
            s = line.strip()
            ln = ln0 + i
            if not s:
                i += 1
                continue
            m = FENCE.match(line)
            if m:
                j = fence_end(lines, i, m.group(2))
                if j is None:
                    self.log("ERROR", ln, "code fence is never closed")
                    j = n
                out.append(self.fence(m.group(3), dedent(lines[i + 1:j], len(m.group(1))), ln))
                i = j + 1
                continue
            m = DIRECTIVE.match(s)
            if m:
                kind, arg = m.group(1).lower(), m.group(2).strip()
                if kind in HATNOTES:
                    out.append(f'<div class="hatnote">{HATNOTES[kind]}{self.inline(arg)}</div>')
                    i += 1
                    continue
                j = directive_end(lines, i)
                if j is None:
                    self.log("ERROR", ln, f":::{kind} is never closed by a line containing only :::")
                    j = n
                out.append(self.directive(kind, arg, lines[i + 1:j], ln + 1, ln))
                i = j + 1
                continue
            if s == ":::":
                self.log("ERROR", ln, "stray ::: with no open block")
                i += 1
                continue
            m = HEADING.match(s)
            if m:
                out.append(self.heading(len(m.group(1)), m.group(2), ln, top))
                i += 1
                continue
            m = FOOTDEF.match(s)
            if m:
                buf = [m.group(2)]
                i += 1
                while i < n and lines[i].startswith(("  ", "\t")) and lines[i].strip():
                    buf.append(lines[i].strip())
                    i += 1
                if m.group(1) in self.notes:
                    self.log("ERROR", ln, f"footnote [^{m.group(1)}] is defined twice")
                self.notes[m.group(1)] = (" ".join(buf), ln)
                continue
            if s.startswith("|") and i + 1 < n and TABLE_SEP.match(lines[i + 1].strip()):
                j = i
                while j < n and lines[j].strip().startswith("|"):
                    j += 1
                out.append(self.table(lines[i:j], ln))
                i = j
                continue
            if s.startswith(">"):
                j, buf = i, []
                while j < n and lines[j].strip():
                    t = lines[j].lstrip()
                    buf.append(re.sub(r"^>\s?", "", t) if t.startswith(">") else t)
                    j += 1
                out.append("<blockquote>" + "\n".join(self.blocks(buf, ln)) + "</blockquote>")
                i = j
                continue
            if LIST.match(line):
                block, i = self.list_block(lines, i, ln0)
                out.append(block)
                continue
            m = IMAGE.match(s)
            if m:
                out.append(self.image(m.group(1), m.group(2), m.group(3), ln))
                i += 1
                continue
            if HR.match(s):
                out.append("<hr>")
                i += 1
                continue
            if i + 1 < n and lines[i + 1].startswith(": "):
                pairs, i = self.dl_pairs(lines, i, ln0)
                out.append(self.dl(pairs))
                continue
            j, buf = i, []
            while j < n and lines[j].strip():
                if j > i and (self.interrupts(lines[j]) or (j + 1 < n and lines[j + 1].startswith(": "))):
                    break
                buf.append(lines[j].strip())
                j += 1
            out.append(f"<p>{self.inline(chr(10).join(buf))}</p>")
            i = j
        return out

    def heading(self, level, text, ln, top):
        if level == 1:
            self.log("ERROR", ln, "use ## for sections; the page title comes from front matter")
            level = 2
        if level > 4:
            self.log("WARN", ln, "headings deeper than #### are shown as ####")
            level = 4
        h = self.inline(text)
        hid = self.unique_id(slugify(text))
        if level <= 3:
            self.heads.append((level, hid, h))
        if level == 2 and top:
            self.sections.append([plain(text), 0, ln])
        return f'<h{level} id="{hid}">{h}</h{level}>'

    def list_block(self, lines, i, ln0):
        m = LIST.match(lines[i])
        ind, ordered = len(m.group(1)), m.group(2)[0].isdigit()
        start = int(re.match(r"\d+", m.group(2)).group()) if ordered else 1
        items, n, j = [], len(lines), i
        while j < n:
            line = lines[j]
            mm = LIST.match(line)
            if mm and len(mm.group(1)) == ind and mm.group(2)[0].isdigit() == ordered:
                gap = len(mm.group(3)) if len(mm.group(3)) <= 4 else 1
                items.append({"ln": ln0 + j, "cind": ind + len(mm.group(2)) + gap, "lines": [mm.group(4)]})
                j += 1
                continue
            cur = items[-1]
            nind = len(line) - len(line.lstrip())
            if not line.strip():
                k = j + 1
                while k < n and not lines[k].strip():
                    k += 1
                if k < n:
                    nxt = lines[k]
                    sib = LIST.match(nxt)
                    deeper = len(nxt) - len(nxt.lstrip()) >= min(cur["cind"], ind + 2)
                    if deeper or (sib and len(sib.group(1)) == ind and sib.group(2)[0].isdigit() == ordered):
                        cur["lines"].append("")
                        j += 1
                        continue
                break
            if nind >= min(cur["cind"], ind + 2):
                cur["lines"].append(line[min(nind, cur["cind"]):])
                j += 1
                continue
            if cur["lines"][-1].strip() and not self.interrupts(line):
                cur["lines"].append(line.strip())
                j += 1
                continue
            break
        lis = []
        for it in items:
            parts = self.blocks(it["lines"], it["ln"])
            if parts and parts[0].startswith("<p>"):
                parts[0] = parts[0][3:-4]
            lis.append("<li>" + "\n".join(parts) + "</li>")
        tag = "ol" if ordered else "ul"
        st = f' start="{start}"' if ordered and start != 1 else ""
        return f"<{tag}{st}>" + "".join(lis) + f"</{tag}>", j

    def dl_pairs(self, lines, i, ln0):
        pairs, n = [], len(lines)
        while i < n:
            if not lines[i].strip():
                k = i
                while k < n and not lines[k].strip():
                    k += 1
                if k + 1 < n and lines[k + 1].startswith(": ") and not self.interrupts(lines[k]):
                    i = k
                    continue
                break
            if not (i + 1 < n and lines[i + 1].startswith(": ")):
                break
            term, tln, defs = lines[i].strip(), ln0 + i, []
            i += 1
            while i < n and lines[i].startswith(": "):
                buf, dln = [lines[i][2:]], ln0 + i
                i += 1
                while i < n and (lines[i].startswith("  ") or
                                 (not lines[i].strip() and i + 1 < n and lines[i + 1].startswith("  "))):
                    buf.append(lines[i][2:])
                    i += 1
                defs.append((buf, dln))
            pairs.append((term, tln, defs))
        return pairs, i

    def dl(self, pairs):
        out = []
        for term, _, defs in pairs:
            out.append(f"<dt>{self.inline(term)}</dt>")
            out.extend("<dd>" + "\n".join(self.blocks(buf, dln)) + "</dd>" for buf, dln in defs)
        return "<dl>" + "".join(out) + "</dl>"

    def table(self, rows, ln):
        def cells(row):
            row = row.strip()
            row = row[1:] if row.startswith("|") else row
            row = row[:-1] if row.endswith("|") and not row.endswith("\\|") else row
            out, buf, code, k = [], [], False, 0
            while k < len(row):
                c = row[k]
                if c == "\\" and k + 1 < len(row) and row[k + 1] == "|":
                    buf.append("|")
                    k += 2
                    continue
                if c == "`":
                    code = not code
                if c == "|" and not code:
                    out.append("".join(buf).strip())
                    buf = []
                else:
                    buf.append(c)
                k += 1
            out.append("".join(buf).strip())
            return out

        head = cells(rows[0])
        aligns = []
        for c in cells(rows[1]):
            aligns.append(' style="text-align:center"' if c.startswith(":") and c.endswith(":")
                          else ' style="text-align:right"' if c.endswith(":") else "")
        aligns += [""] * len(head)
        out = ['<div class="table-wrap"><table class="wikitable"><thead><tr>']
        out += [f'<th scope="col"{aligns[k]}>{self.inline(c)}</th>' for k, c in enumerate(head)]
        out.append("</tr></thead><tbody>")
        for r, row in enumerate(rows[2:]):
            c = cells(row)
            if len(c) != len(head):
                self.log("WARN", ln + 2 + r, f"table row has {len(c)} cells; the header has {len(head)}")
            c = (c + [""] * len(head))[:len(head)]
            out.append("<tr>" + "".join(f"<td{aligns[k]}>{self.inline(x)}</td>" for k, x in enumerate(c)) + "</tr>")
        out.append("</tbody></table></div>")
        return "".join(out)

    def image(self, alt, url, title, ln):
        self.figures += 1
        if not alt:
            self.log("WARN", ln, "image needs alt text")
        host = urlsplit(url).netloc
        credit = f' <span class="credit">Image: {esc(host)}.</span>' if host else ""
        return (f'<figure class="image"><img src="{attr(url)}" alt="{attr(alt)}" loading="lazy">'
                f'<figcaption><span class="fig-n">Figure {self.figures}.</span>{self.inline(title or alt)}'
                f'{credit}</figcaption></figure>')

    # ----- inline -----

    def inline(self, text, ph=False, in_link=False):
        out, pos = [], 0
        for m in INLINE.finditer(text):
            if m.start() > pos:
                out.append(smart(text[pos:m.start()], text[pos - 1] if pos else " "))
            pos = m.end()
            g = m.group
            if g("code") is not None:
                c = g("ct")
                if len(c) > 2 and c[0] == " " and c[-1] == " " and c.strip():
                    c = c[1:-1]
                nw = ' class="nw"' if len(c) <= 28 else ""
                c = esc(c)
                out.append(f"<code{nw}>" + (PH.sub(r"<var>\1</var>", c) if ph else c) + "</code>")
            elif g("fn") is not None:
                out.append(self.cite(g("fk")))
            elif g("img") is not None:
                out.append(f'<img class="inline" src="{attr(g("iu"))}" alt="{attr(g("ia"))}">')
            elif g("link") is not None:
                if in_link:
                    out.append(esc(m.group(0)))
                    continue
                title = f' title="{attr(g("ltitle"))}"' if g("ltitle") else ""
                out.append(f'<a href="{attr(self.href(g("lu")))}"{title}>{self.inline(g("lt"), ph, True)}</a>')
            elif g("auto") is not None:
                out.append(f'<a href="{attr(g("au"))}">{esc(g("au"))}</a>')
            elif g("strong") is not None:
                out.append(f"<strong>{self.inline(g('st'), ph, in_link)}</strong>")
            elif g("em") is not None:
                out.append(f"<em>{self.inline(g('et'), ph, in_link)}</em>")
            elif g("em2") is not None:
                out.append(f"<em>{self.inline(g('e2t'), ph, in_link)}</em>")
            elif g("esc") is not None:
                out.append(esc(g("ec")))
        if pos < len(text):
            out.append(smart(text[pos:], text[pos - 1] if pos else " "))
        return "".join(out)

    def cite(self, key):
        self.uses[key] = self.uses.get(key, 0) + 1
        if self.sections:
            self.sections[-1][1] += 1
        return f"\x00F{key}\x01{self.uses[key]}\x00"

    def href(self, url):
        u = html.unescape(url.strip())
        if re.match(r"(?i)^\s*(javascript|vbscript|data):", u):
            self.log("WARN", 0, f"unsafe link removed: {u[:40]}")
            return "#"
        m = re.match(r"^(?:\./)?([\w.-]+)\.md(?:#([\w-]+))?$", u)
        if m:
            pid = "start" if m.group(1) == "index" else m.group(1)
            target = f"{pid}--{m.group(2)}" if m.group(2) else pid
            self.internal.append(target)
            return "#" + target
        if u.startswith("#") and len(u) > 1:
            frag = u[1:]
            target = frag if frag in self.bundle.slugs or "--" in frag else f"{self.id}--{frag}"
            self.internal.append(target)
            return "#" + target
        return u

    # ----- fenced code and diagrams -----

    def fence(self, info, body, ln, ph=False, extra=""):
        lang, _, rest = info.strip().partition(" ")
        lang, rest = lang.lower(), rest.strip()
        base, _, opt = lang.partition(":")
        base = "sequence" if base == "seq" else base
        if base in DIAGRAM_LIMITS:
            return self.diagram(base, opt, rest, body, ln)
        code = "\n".join(body)
        self.code_words += words(code)
        self.code_blocks += 1
        if base == "output":
            return (f'<figure class="code output"><figcaption><span>{esc(rest or "Output")}</span></figcaption>'
                    f"<pre><code>{esc(code)}</code></pre></figure>")
        cap = ""
        if rest:
            lang_tag = f'<span class="code-lang">{esc(base)}</span>' if base else ""
            cap = f'<figcaption><span class="code-label">{esc(rest)}</span><span class="cap-right">{lang_tag}</span></figcaption>'
        return f'<figure class="code{extra}">{cap}<pre><code>{highlight(code, base, ph)}</code></pre></figure>'

    def diagram(self, kind, opt, caption, body, ln):
        lines = [l for l in body if l.strip() and not l.strip().startswith("//")]
        extra, count = "", 0
        if kind == "svg":
            inner = sanitize_svg("\n".join(body))
            if not inner.lower().startswith("<svg"):
                self.log("ERROR", ln, "svg block must contain a single <svg> element")
        elif kind == "flow":
            inner, count, vertical = self.d_flow(lines, opt)
            extra = " v" if vertical else ""
        elif kind == "sequence":
            inner, count = self.d_seq(lines, ln)
        elif kind == "stack":
            inner, count = self.d_stack(lines)
        elif kind == "tree":
            inner, count = self.d_tree(lines)
        else:
            inner, count = self.d_nest(lines)
        limit = DIAGRAM_LIMITS[kind]
        if limit and count > limit:
            self.log("WARN", ln, f"{kind} diagram has {count} items; keep it to {limit} or split it")
        if not caption:
            self.log("WARN", ln, f"{kind} diagram has no caption; say what the reader should notice")
        self.figures += 1
        cap = f'<figcaption><span class="fig-n">Figure {self.figures}.</span>{self.inline(caption)}</figcaption>'
        return f'<figure class="dg {kind}{extra}">{inner}{cap}</figure>'

    def flow_item(self, label, note):
        n = f'<span class="fl-note">{self.inline(note)}</span>' if note else ""
        return f'<span class="fl-label">{self.inline(label)}</span>{n}'

    def d_flow(self, lines, opt):
        nodes, labels, loop, pending = [], {}, None, None
        for line in lines:
            s = line.strip()
            if s.startswith("->"):
                pending = s[2:].strip()
                continue
            if s.lower().startswith("loop:"):
                loop = s[5:].strip()
                continue
            if nodes and pending:
                labels[len(nodes) - 1] = pending
            pending = None
            nodes.append([split_note(a) for a in re.split(r"\s+\|\s+", s)])
        size = sum(len(a) + len(b or "") for alts in nodes for a, b in alts)
        vertical = opt == "v" or (opt != "h" and (len(nodes) > 5 or size > 280))
        arrow = ('<svg class="fl-arrow" viewBox="0 0 32 12" aria-hidden="true">'
                 '<path d="M1 6H30M25 1.5L30 6L25 10.5"/></svg>')
        parts = []
        for k, alts in enumerate(nodes):
            if k:
                lab = labels.get(k - 1)
                lab = f'<span class="fl-elabel">{self.inline(lab)}</span>' if lab else ""
                parts.append(f'<div class="fl-edge">{lab}{arrow}</div>')
            if len(alts) == 1:
                parts.append(f'<div class="fl-node">{self.flow_item(*alts[0])}</div>')
            else:
                inner = '<span class="fl-or">or</span>'.join(
                    f'<span class="fl-alt">{self.flow_item(*a)}</span>' for a in alts)
                parts.append(f'<div class="fl-node">{inner}</div>')
        loop_html = ""
        if loop:
            loop_html = (f'<div class="fl-loop" aria-hidden="true"></div>'
                         f'<div class="fl-loop-label">↺ {self.inline(loop)}</div>')
        return f'<div class="fl-track">{"".join(parts)}</div>{loop_html}', len(nodes), vertical

    def d_seq(self, lines, ln):
        parts, rows = [], []

        def pid(name):
            name = name.strip()
            if name not in parts:
                parts.append(name)
            return parts.index(name)

        for line in lines:
            s = line.strip()
            m = re.match(r"(?i)^participant\s+(.+)$", s)
            if m:
                pid(m.group(1))
                continue
            m = re.match(r"(?i)^note\s+(.+?)\s*:\s*(.+)$", s)
            if m:
                who = [pid(x) for x in m.group(1).split(",")]
                rows.append(("note", min(who), max(who), plain(m.group(2)), False))
                continue
            m = re.match(r"^(.+?)\s*(-->|->)\s*(.+?)\s*:\s*(.*)$", s)
            if m:
                rows.append(("msg", pid(m.group(1)), pid(m.group(3)), plain(m.group(4)), m.group(2) == "-->"))
                continue
            self.log("WARN", ln, f"sequence line not understood: {s[:50]}")
        if not parts:
            return "", 0
        cw, lw, padx, top, bh = 7.6, 7.0, 6, 8, 30
        for kind, a, b, text, _ in rows:
            if len(text) > 56:
                self.log("WARN", ln, f"sequence label over 56 characters: {text[:40]}...")
        span = max(max(90, len(p) * cw + 26) for p in parts) + 24
        for kind, a, b, text, _ in rows:
            w = len(text) * lw + 30
            if kind == "msg" and a != b:
                span = max(span, w / abs(b - a))
            elif kind == "note":
                span = max(span, (w + 10) / (b - a + 1))

        def x(i):
            return padx + span / 2 + i * span

        y, g = top + bh + 24, []
        extra = 0.0
        for kind, a, b, text, reply in rows:
            rc = " reply" if reply else ""
            if kind == "note":
                if a == b:
                    w = len(text) * lw + 22
                    x0 = x(a) - w / 2
                else:
                    x0, w = x(a) - span / 2 + 10, x(b) - x(a) + span - 20
                g.append(f'<rect class="sq-note" x="{x0:.1f}" y="{y - 15:.1f}" width="{w:.1f}" height="24"/>')
                g.append(f'<text class="sq-lab" x="{x0 + w / 2:.1f}" y="{y + 1.5:.1f}" text-anchor="middle">{esc(text)}</text>')
                y += 36
            elif a == b:
                xa = x(a)
                extra = max(extra, xa + 40 + len(text) * lw - (x(len(parts) - 1) + span / 2))
                g.append(f'<text class="sq-lab" x="{xa + 40:.1f}" y="{y + 6:.1f}">{esc(text)}</text>')
                g.append(f'<path class="sq-msg{rc}" d="M{xa + 1:.1f} {y - 6:.1f}H{xa + 30:.1f}V{y + 12:.1f}H{xa + 9:.1f}"/>')
                g.append(f'<path class="sq-head{rc}" d="M{xa + 1:.1f} {y + 12:.1f}L{xa + 9:.1f} {y + 8:.1f}L{xa + 9:.1f} {y + 16:.1f}Z"/>')
                y += 42
            else:
                x1, x2 = x(a), x(b)
                d = 1 if x2 > x1 else -1
                g.append(f'<text class="sq-lab" x="{(x1 + x2) / 2:.1f}" y="{y - 7:.1f}" text-anchor="middle">{esc(text)}</text>')
                g.append(f'<path class="sq-msg{rc}" d="M{x1 + d:.1f} {y:.1f}H{x2 - 9 * d:.1f}"/>')
                g.append(f'<path class="sq-head{rc}" d="M{x2 - d:.1f} {y:.1f}L{x2 - 9 * d:.1f} {y - 4:.1f}L{x2 - 9 * d:.1f} {y + 4:.1f}Z"/>')
                y += 40
        height = y - 10
        width = x(len(parts) - 1) + span / 2 + padx + max(0.0, extra + 8)
        frame = []
        for i, p in enumerate(parts):
            bw = max(90, len(p) * cw + 26)
            frame.append(f'<line class="sq-life" x1="{x(i):.1f}" y1="{top + bh:.1f}" x2="{x(i):.1f}" y2="{height:.1f}"/>')
            frame.append(f'<rect class="sq-box" x="{x(i) - bw / 2:.1f}" y="{top}" width="{bw:.1f}" height="{bh}"/>')
            frame.append(f'<text class="sq-who" x="{x(i):.1f}" y="{top + bh / 2 + 4.5:.1f}" text-anchor="middle">{esc(plain(p))}</text>')
        label = "Sequence diagram: " + ", ".join(plain(p) for p in parts)
        svg = (f'<svg class="seq-svg" viewBox="0 0 {width:.0f} {height:.0f}" width="{width:.0f}" height="{height:.0f}" '
               f'style="min-width:{width * 0.62:.0f}px" role="img" aria-label="{attr(label)}">'
               + "".join(frame) + "".join(g) + "</svg>")
        return f'<div class="dg-scroll">{svg}</div>', len(rows)

    def d_stack(self, lines):
        axis, items = None, []
        for line in lines:
            s = line.strip()
            if s[:2] in ("^ ", "v "):
                axis = ("up" if s[0] == "^" else "down", s[2:].strip())
                continue
            hi = s.startswith("* ")
            items.append((hi,) + split_note(s[2:] if hi else s))
        axis_html = f'<div class="st-axis {axis[0]}"><span>{self.inline(axis[1])}</span></div>' if axis else ""
        lis = []
        for hi, label, note in items:
            cls = ' class="hi"' if hi else ""
            n = f'<span class="st-note">{self.inline(note)}</span>' if note else ""
            lis.append(f'<li{cls}><span class="st-label">{self.inline(label)}</span>{n}</li>')
        return f'<div class="st-wrap">{axis_html}<ol class="st">{"".join(lis)}</ol></div>', len(items)

    def d_tree(self, lines):
        items = []
        for line in lines:
            raw = line.rstrip()
            body = raw.strip()
            m = re.match(r"^(.*?)\s+#\s?(.*)$", body)
            name, com = (m.group(1), m.group(2)) if m else (body, "")
            items.append([len(raw) - len(raw.lstrip()), name, com])
        levels = sorted({it[0] for it in items})
        for it in items:
            it[0] = levels.index(it[0])
        n = len(items)

        def last(idx, depth):
            for j in range(idx + 1, n):
                if items[j][0] < depth:
                    return True
                if items[j][0] == depth:
                    return False
            return True

        rows = []
        for k, (d, name, com) in enumerate(items):
            prefix = ""
            if d:
                for dd in range(1, d):
                    anc = [j for j in range(k) if items[j][0] == dd]
                    prefix += "    " if not anc or last(anc[-1], dd) else "│   "
                prefix += "└── " if last(k, d) else "├── "
            rows.append((prefix, name, com))
        width = max((len(p) + len(nm) for p, nm, _ in rows), default=0)
        out = []
        for p, nm, com in rows:
            cls = "t-dir" if nm.endswith("/") else "t-name"
            line = f'<span class="t-pre">{esc(p)}</span><span class="{cls}">{esc(nm)}</span>'
            if com:
                line += " " * (width - len(p) - len(nm) + 3) + f'<span class="t-com">{esc(com)}</span>'
            out.append(line)
        return f'<pre class="tree-pre">{chr(10).join(out)}</pre>', n

    def d_nest(self, lines):
        root = {"kids": [], "ind": -1}
        stack = [root]
        for line in lines:
            ind = len(line) - len(line.lstrip())
            label, note = split_note(line.strip())
            node = {"label": label, "note": note, "kids": [], "ind": ind}
            while stack[-1]["ind"] >= ind:
                stack.pop()
            stack[-1]["kids"].append(node)
            stack.append(node)

        def render(node, depth):
            note = f'<span class="nest-note">{self.inline(node["note"])}</span>' if node["note"] else ""
            kids = "".join(render(k, depth + 1) for k in node["kids"])
            kids = f'<div class="nest-kids">{kids}</div>' if kids else ""
            return (f'<div class="nest-box d{min(depth, 3)}"><div class="nest-head">'
                    f'<span class="nest-label">{self.inline(node["label"])}</span>{note}</div>{kids}</div>')

        body = "".join(render(k, 0) for k in root["kids"])
        if len(root["kids"]) > 1:
            body = f'<div class="nest-kids">{body}</div>'
        return body, len(lines)

    # ----- containers -----

    def directive(self, kind, arg, inner, iln, ln):
        if kind in CALLOUTS or kind == "background":
            parts = self.blocks(inner, iln)
            if kind == "background":
                self.has["background"] += 1
                head = ('<span class="label">Background</span>'
                        '<span class="aside">General knowledge, not from the source documentation.</span>')
                title = f'<h4 class="callout-title">{self.inline(arg)}</h4>' if arg else ""
                return f'<aside class="background"><p class="callout-head">{head}</p>{title}{"".join(parts)}</aside>'
            label = f'<span class="label">{CALLOUTS[kind]}</span>'
            if arg:
                head = f'<p class="callout-head">{label}<span class="callout-title">{self.inline(arg)}</span></p>'
                return f'<aside class="callout {kind}">{head}{"".join(parts)}</aside>'
            if parts and parts[0].startswith("<p>"):
                parts[0] = "<p>" + label + parts[0][3:]
            else:
                parts.insert(0, f'<p class="callout-head">{label}</p>')
            return f'<aside class="callout {kind}">{"".join(parts)}</aside>'
        if kind == "infobox":
            if self.infobox is not None:
                self.log("ERROR", ln, "only one :::infobox per page")
            self.infobox = (arg, inner, iln)
            return ""
        if kind == "example":
            return self.example(arg, inner, iln, ln)
        if kind == "recipes":
            return self.recipes(inner, iln, ln)
        if kind == "exercise":
            self.has["practice"] += 1
            if not any(re.match(r"^[*_]*check[*_]*\s*:", l.strip(), re.I) for l in inner):
                self.log("WARN", ln, "exercise has no 'Check:' line saying how the reader knows it worked")
            title = f'<span class="callout-title">{self.inline(arg)}</span>' if arg else ""
            body = "\n".join(self.blocks(inner, iln))
            return f'<section class="exercise"><p class="callout-head"><span class="label">Exercise</span>{title}</p>{body}</section>'
        if kind == "recall":
            k = 0
            while k < len(inner) and not inner[k].strip():
                k += 1
            pairs, end = self.dl_pairs(inner, k, iln)
            if any(l.strip() for l in inner[end:]) or not pairs:
                self.log("WARN", ln, "recall expects question lines, each followed by an ': answer' line")
            items = []
            for term, _, defs in pairs:
                ans = "".join("\n".join(self.blocks(buf, dln)) for buf, dln in defs)
                items.append(f'<li><details><summary>{self.inline(term)}</summary><div class="answer">{ans}</div></details></li>')
            self.has["recall"] += len(items)
            return f'<ol class="recall">{"".join(items)}</ol>'
        if kind == "pages":
            return "\x00PAGES\x00"
        self.log("ERROR", ln, f"unknown block :::{kind} (known: {', '.join(sorted(CONTAINERS | set(HATNOTES)))})")
        return "\n".join(self.blocks(inner, iln))

    def example(self, title, inner, iln, ln):
        self.has["practice"] += 1
        rows, prose, pln, k = [], [], iln, 0
        while k < len(inner):
            m = FENCE.match(inner[k])
            if not m:
                prose.append(inner[k])
                k += 1
                continue
            end = fence_end(inner, k, m.group(2))
            if end is None:
                self.log("ERROR", iln + k, "code fence is never closed")
                end = len(inner)
            info = m.group(3).strip()
            code = self.fence(info, dedent(inner[k + 1:end], len(m.group(1))), iln + k)
            if info.split(" ")[0].lower() == "output" and rows and not any(l.strip() for l in prose):
                rows[-1][1].append(code)
            else:
                rows.append([(prose, pln), [code]])
            prose, pln, k = [], iln + end + 1, end + 1
        if any(l.strip() for l in prose):
            rows.append([(prose, pln), []])
        if not any(codes for _, codes in rows):
            self.log("WARN", ln, "example has no code; write plain paragraphs instead")
        out = []
        for (p, pl), codes in rows:
            docs = "\n".join(self.blocks(p, pl))
            cls = "ex-code" if codes else "ex-code empty"
            out.append(f'<div class="ex-row"><div class="ex-docs">{docs}</div><div class="{cls}">{"".join(codes)}</div></div>')
        t = f'<span class="callout-title">{self.inline(title)}</span>' if title else ""
        return f'<figure class="example"><figcaption><span class="label">Example</span>{t}</figcaption>{"".join(out)}</figure>'

    def recipes(self, inner, iln, ln):
        self.has["practice"] += 1
        items, k = [], 0
        while k < len(inner):
            line, s = inner[k], inner[k].strip()
            if not s:
                k += 1
                continue
            m = FENCE.match(line)
            if m:
                end = fence_end(inner, k, m.group(2)) or len(inner)
                if items:
                    body = dedent(inner[k + 1:end], len(m.group(1)))
                    items[-1]["code"].append(self.fence(m.group(3) or "sh", body, iln + k, ph=True, extra=" cmd"))
                else:
                    self.log("WARN", iln + k, "recipe code before any '- description:' line")
                k = end + 1
                continue
            if s.startswith("- "):
                items.append({"desc": [s[2:]], "code": [], "ln": iln + k})
                k += 1
                continue
            cm = re.match(r"^(`+)\s?(.+?)\s?\1$", s)
            if cm and items:
                self.code_words += words(cm.group(2))
                self.code_blocks += 1
                items[-1]["code"].append(f'<figure class="code cmd"><pre><code>{highlight(cm.group(2), "sh", True)}</code></pre></figure>')
                k += 1
                continue
            if items and not items[-1]["code"]:
                items[-1]["desc"].append(s)
            else:
                self.log("WARN", iln + k, "text in :::recipes must be '- description:' followed by a `command` line")
            k += 1
        if len(items) > MAX_RECIPES:
            self.log("WARN", ln, f"{len(items)} recipes; keep the {MAX_RECIPES} most common and move the rest to a reference table")
        lis = []
        for it in items:
            if not it["code"]:
                self.log("WARN", it["ln"], "recipe has no command")
            lis.append(f'<li><p class="rc-desc">{self.inline(" ".join(it["desc"]))}</p>{"".join(it["code"])}</li>')
        return f'<ul class="recipes">{"".join(lis)}</ul>'

    # ----- infobox and references -----

    def render_infobox(self):
        if not self.infobox:
            return ""
        arg, inner, iln = self.infobox
        rows = []
        for k, line in enumerate(inner):
            s = line.strip()
            if not s:
                continue
            if s.startswith("## "):
                rows.append(f'<tr><th colspan="2" class="ib-group">{self.inline(s[3:])}</th></tr>')
                continue
            m = IMAGE.match(s)
            if m:
                cap = f"<figcaption>{self.inline(m.group(3))}</figcaption>" if m.group(3) else ""
                rows.append(f'<tr><td colspan="2" class="ib-image"><figure><img src="{attr(m.group(2))}" '
                            f'alt="{attr(m.group(1))}" loading="lazy">{cap}</figure></td></tr>')
                continue
            m = re.match(r"^([^:]{1,40}):\s+(.+)$", s)
            if not m:
                self.log("WARN", iln + k, "infobox lines are 'Label: value', '## Group' or an image")
                continue
            rows.append(f'<tr><th scope="row">{self.inline(m.group(1))}</th><td>{self.inline(m.group(2))}</td></tr>')
        return (f'<table class="infobox"><tbody><tr><th colspan="2" class="ib-title">{self.inline(arg) if arg else esc(self.title)}</th></tr>'
                + "".join(rows) + "\x00IBAUTO\x00</tbody></table>")

    def parse_note(self, key):
        if key in self.parsed:
            return self.parsed[key]
        text, ln = self.notes[key]
        m = NOTE_QUOTE.match(text)
        if m:
            q, u = m.group("q"), m.group("u")
            label = m.group("l") or self.bundle.sources.label(u)
            ok = self.bundle.sources.contains(q, u)
            self.quotes += 1
            if ok:
                self.verified += 1
            if ok is False:
                self.log("WARN", ln, f"quote [^{key}] not found in the fetched source: \"{q[:60]}\"")
            if words(q) > MAX_QUOTE_WORDS:
                self.log("WARN", ln, f"quote [^{key}] has {words(q)} words; quote one claim, at most {MAX_QUOTE_WORDS}")
            info = {"q": q, "u": u, "label": label, "ok": ok}
        else:
            m = NOTE_URL.match(text)
            if m:
                info = {"q": None, "u": m.group("u"), "label": m.group("l") or self.bundle.sources.label(m.group("u")), "ok": None}
            else:
                info = {"q": None, "u": None, "label": None, "ok": None, "text": text}
        self.parsed[key] = info
        return info

    def number_refs(self, s):
        def rep(m):
            key, k = m.group(1), int(m.group(2))
            if key not in self.notes:
                return '<sup class="ref">[?]</sup>'
            if key not in self.num:
                self.num[key] = len(self.num) + 1
            n, info = self.num[key], self.parse_note(key)
            tip = (f"“{plain(info['q'])}” — {info['label']}" if info["q"]
                   else info["label"] or plain(info.get("text", "")))
            return f'<sup class="ref" id="{self.id}-r{n}-{k}"><a href="#{self.id}-n{n}" title="{attr(tip)}">[{n}]</a></sup>'
        return re.sub(r"\x00F(.+?)\x01(\d+)\x00", rep, s)

    def references(self):
        if not self.num:
            return ""
        items = []
        for key, n in sorted(self.num.items(), key=lambda kv: kv[1]):
            info, uses = self.parse_note(key), self.uses[key]
            if uses == 1:
                back = f'<a href="#{self.id}-r{n}-1" aria-label="Back to the text">^</a>'
            else:
                back = "^ " + " ".join(f'<a href="#{self.id}-r{n}-{k}">{chr(96 + k)}</a>' for k in range(1, uses + 1))
            if info["q"]:
                body = f'<q>{self.inline(info["q"])}</q> <cite><a href="{attr(info["u"])}">{esc(info["label"])}</a></cite>'
                if info["ok"] is False:
                    body += ' <span class="unverified">(not found in the fetched copy)</span>'
            elif info["u"]:
                body = f'<cite><a href="{attr(info["u"])}">{esc(info["label"])}</a></cite>'
            else:
                body = self.inline(info["text"])
            items.append(f'<li id="{self.id}-n{n}"><span class="back">{back}</span>{body}</li>')
        hid = self.unique_id("references")
        self.heads.append((2, hid, "References"))
        return f'<h2 id="{hid}">References</h2><ol class="references">{"".join(items)}</ol>'

    # ----- final assembly of one page -----

    def finish(self):
        """Number citations, run page-level checks, and return the article body pieces."""
        box = self.number_refs(self.render_infobox())
        body = self.number_refs(self.body)
        for key in self.uses:
            if key not in self.notes:
                self.log("ERROR", 0, f"[^{key}] is cited but never defined")
        for key, (_, ln) in self.notes.items():
            if key not in self.uses:
                self.log("WARN", ln, f"footnote [^{key}] is defined but never cited")
        text = strip_tags(body)
        prose = max(0, words(text) - self.code_words)
        self.minutes = max(1, math.ceil((prose + 1.5 * self.code_words) / WPM))
        lead = strip_tags(re.sub(r'<div class="hatnote">.*?</div>', "", body.split("<h2", 1)[0]))
        if not self.is_start:
            if not words(lead):
                self.log("WARN", 0, "no lead: open with 2-4 sentences that define the subject and say why it matters")
            elif words(lead) > MAX_LEAD_WORDS:
                self.log("WARN", 0, f"lead is {words(lead)} words; keep it under {MAX_LEAD_WORDS} and move detail into sections")
            if not self.infobox:
                self.log("WARN", 0, "no :::infobox with the facts a reader looks up first")
            if self.has["recall"] < 3:
                self.log("WARN", 0, f"{self.has['recall']} :::recall questions; add at least 3")
            if not self.has["practice"] and not self.code_blocks:
                self.log("WARN", 0, "nothing hands-on: add an :::example, :::recipes or :::exercise")
            if not self.uses:
                self.log("WARN", 0, "no citations; back claims about the subject with [^key] quotes")
            uncited = [t for t, c, _ in self.sections if not c and not UNCITED_OK.search(t)]
            if uncited:
                self.log("NOTE", 0, "sections without citations: " + "; ".join(uncited))
            for key in ("summary", "source"):
                if not self.meta.get(key):
                    self.log("WARN", 1, f"front matter has no {key}:")
            if self.minutes > LONG_PAGE_MIN:
                self.log("NOTE", 0, f"reads in about {self.minutes} min; consider splitting it")
        return box, body


# ---------- bundle ----------

class Bundle:
    def __init__(self, root):
        self.root = root
        self.sources = Sources(root / "src")
        files = sorted((root / "pages").glob("*.md"))
        self.slugs = {"start" if p.stem == "index" else p.stem for p in files}
        pages = [Page(p, self) for p in files]
        self.start = next((p for p in pages if p.is_start), None)
        rest = [p for p in pages if not p.is_start]
        order = [s.strip() for s in (self.start.meta.get("order", "") if self.start else "").split(",") if s.strip()]
        for s in order:
            if s not in {p.slug for p in rest}:
                LOG.add("WARN", "pages/index.md", f"order lists '{s}' but pages/{s}.md does not exist")
        rest.sort(key=lambda p: (order.index(p.slug) if p.slug in order else len(order), p.slug))
        self.rest = rest
        self.order = ([self.start] if self.start else []) + rest
        if not self.start and len(rest) > 1:
            LOG.add("WARN", "pages/", "several pages but no pages/index.md start page (title, order, overview)")
        if not self.sources.norm:
            LOG.add("WARN", "src/", "no fetched sources; quotes were not verified")
        first = self.start or (rest[0] if rest else None)
        source = (first.meta.get("source") if first else "") or ""
        self.title = (self.start.title if self.start else
                      rest[0].title if len(rest) == 1 else f"{urlsplit(source).netloc or 'Documentation'} summaries")
        self.source = source
        self.fetched = (first.meta.get("fetched") if first else "") or dt.date.today().isoformat()


def toc_sections(page):
    items, n2 = [], 0
    for level, hid, h in page.heads:
        if level == 2:
            n2, n3 = n2 + 1, 0
            items.append([f'<a href="#{hid}"><span class="tn">{n2}</span>{h}</a>', []])
        elif level == 3 and items:
            n3 += 1
            items[-1][1].append(f'<li><a href="#{hid}"><span class="tn">{n2}.{n3}</span>{h}</a></li>')
    if not items:
        return ""
    lis = "".join(f"<li>{a}" + (f'<ol class="toc-secs">{"".join(sub)}</ol>' if sub else "") + "</li>"
                  for a, sub in items)
    return f'<ol class="toc-secs">{lis}</ol>'


def navbox(b, current):
    if len(b.rest) < 2:
        return ""
    groups = {}
    for p in b.rest:
        groups.setdefault(p.meta.get("group") or "Pages", []).append(p)
    rows = []
    for g, ps in groups.items():
        links = '<span class="sep" aria-hidden="true">·</span>'.join(
            f'<span class="here">{esc(p.title)}</span>' if p is current else f'<a href="#{p.id}">{esc(p.title)}</a>'
            for p in ps)
        rows.append(f'<tr><th scope="row" class="nb-group">{esc(g)}</th><td>{links}</td></tr>')
    title = f'<a href="#start">{esc(b.title)}</a>' if b.start and current is not b.start else esc(b.title)
    return f'<table class="navbox"><tbody><tr><th colspan="2" class="nb-title">{title}</th></tr>{"".join(rows)}</tbody></table>'


def pager(b, page):
    k = b.order.index(page)
    prev = b.order[k - 1] if k else None
    nxt = b.order[k + 1] if k + 1 < len(b.order) else None
    if not prev and not nxt:
        return ""
    out = ""
    if prev:
        out += f'<a class="prev" href="#{prev.id}"><span>Previous:</span> {esc(prev.title)}</a>'
    if nxt:
        out += f'<a class="next" href="#{nxt.id}"><span>Next:</span> {esc(nxt.title)}</a>'
    return f'<nav class="pager" aria-label="Pages">{out}</nav>'


def contents_table(b, start):
    rows = []
    for k, p in enumerate(b.rest, 1):
        rows.append(f'<tr><td>{k}</td><td><a href="#{p.id}">{esc(p.title)}</a></td>'
                    f'<td>{p.inline(p.meta.get("summary", ""))}</td><td>{p.minutes} min</td></tr>')
    total = sum(p.minutes for p in b.rest)
    return ('<div class="table-wrap"><table class="wikitable contents-table"><thead><tr>'
            '<th scope="col">#</th><th scope="col">Page</th><th scope="col">What it covers</th>'
            f'<th scope="col">Time</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            f'<p class="tagline">{len(b.rest)} pages, about {total} minutes in total.</p>')


def appearance():
    groups = [("size", "Text", [("s", "Small"), ("m", "Standard"), ("l", "Large")]),
              ("width", "Width", [("std", "Standard"), ("wide", "Wide")]),
              ("theme", "Color", [("auto", "Automatic"), ("light", "Light"), ("dark", "Dark")])]
    out = ['<form class="appearance" aria-label="Appearance"><div class="ap-title">Appearance</div>']
    for name, legend, opts in groups:
        out.append(f"<fieldset><legend>{legend}</legend>")
        out += [f'<label><input type="radio" name="{name}" value="{v}"> {t}</label>' for v, t in opts]
        out.append("</fieldset>")
    out.append("</form>")
    return "".join(out)


def document(b):
    articles, toc = [], []
    finished = {p.id: p.finish() for p in b.order}
    for p in b.order:
        box, body = finished[p.id]
        if p.is_start:
            table = contents_table(b, p)
            body = body.replace("\x00PAGES\x00", table) if "\x00PAGES\x00" in body else body + table
        cited = []
        for key in p.num:
            info = p.parse_note(key)
            if info["u"] and canon(info["u"]) not in [canon(u) for u in cited]:
                cited.append(info["u"])
        auto = ""
        if box:
            links = [f'<a href="{attr(u)}">{esc(b.sources.title(u) or short_url(u))}</a>' for u in cited[:4]]
            more = f" and {len(cited) - 4} more" if len(cited) > 4 else ""
            auto = '<tr><th colspan="2" class="ib-group">This summary</th></tr>'
            if links:
                auto += f'<tr><th scope="row">Based on</th><td>{", ".join(links)}{more}</td></tr>'
            if p.quotes:
                checked = (f"{p.verified} of {p.quotes} found in the fetched pages" if b.sources.norm
                           else f"{p.quotes}, not checked")
                auto += f'<tr><th scope="row">Quotes</th><td>{checked}</td></tr>'
            box = box.replace("\x00IBAUTO\x00", auto)
        cut = body.find("<h2")
        lead, rest = (body[:cut], body[cut:]) if cut >= 0 else (body, "")
        body = f'<div class="lead">{lead}</div>{rest}'
        refs = p.references()
        src = p.meta.get("source", "")
        bits = []
        if src:
            bits.append(f'From <a href="{attr(src)}">{esc(short_url(src))}</a>')
        date = p.meta.get("fetched") or b.fetched
        bits.append(f"condensed {esc(nice_date(date))}")
        bits.append(f"{sum(q.minutes for q in b.rest) if p.is_start else p.minutes} min read")
        tagline = '<p class="tagline">' + SEP.join(bits) + "</p>"
        articles.append(
            f'<article class="page" id="{p.id}" data-title="{attr(p.title)}">'
            f'<header><h1>{esc(p.title)}</h1>{tagline}</header>'
            f'<div class="page-body">{box}{body}</div>{refs}{pager(b, p)}{navbox(b, p)}</article>')
        active = ' class="active"' if p is b.order[0] else ""
        name = "Start here" if p.is_start else esc(p.title)
        toc.append(f'<li data-page="{p.id}"{active}><a href="#{p.id}">{name}</a>{toc_sections(p)}</li>')
    known = {p.id for p in b.order} | {hid for p in b.order for hid in p.ids}
    known |= {f"{p.id}-n{n}" for p in b.order for n in p.num.values()}
    for p in b.order:
        for target in p.internal:
            if target not in known:
                LOG.add("WARN", p.where, f"internal link #{target} points nowhere")

    total_q = sum(p.quotes for p in b.order)
    total_v = sum(p.verified for p in b.order)
    minutes = sum(p.minutes for p in b.rest) or sum(p.minutes for p in b.order)
    host = urlsplit(b.source).netloc
    first = b.order[0].id if b.order else "start"
    meta = [f'Condensed from <a href="{attr(b.source)}">{esc(host)}</a>' if host else "Condensed documentation"]
    meta.append(f"{len(b.rest)} page{'s' if len(b.rest) != 1 else ''}")
    meta.append(f"{minutes} min")
    check = (f"{total_v} of {total_q} quoted passages were found in copies fetched on {esc(nice_date(b.fetched))}."
             if b.sources.norm and total_q else "Quoted passages were not checked against fetched copies.")
    css = (ASSETS / "style.css").read_text(encoding="utf-8")
    js = (ASSETS / "app.js").read_text(encoding="utf-8")
    boot = ('document.documentElement.classList.add("js");'
            'try{var a=JSON.parse(localStorage.getItem("tldr-appearance"))||{},r=document.documentElement;'
            '["size","width","theme"].forEach(function(k){if(a[k])r.setAttribute("data-"+k,a[k])})}catch(e){}')
    return f"""<!doctype html>
<html lang="{attr(b.order[0].meta.get('lang', 'en') if b.order else 'en')}" data-theme="auto" data-size="m" data-width="std">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="tldr skill">
<title>{esc(b.title)}</title>
<script>{boot}</script>
{FONTS}
<style>
{css}
</style>
</head>
<body data-bundle="{attr(b.title)}">
<a class="skip" href="#content">Skip to content</a>
<header class="masthead"><a class="mh-title" href="#{first}">{esc(b.title)}</a><span class="mh-meta">{SEP.join(meta)}</span></header>
<div class="layout">
<nav class="toc" aria-label="Contents"><details open><summary>Contents</summary><ol class="toc-pages">{"".join(toc)}</ol>{appearance()}</details></nav>
<main id="content">
{chr(10).join(articles)}
</main>
</div>
<footer class="colophon"><p>A study summary of third-party documentation, written with the tldr skill. {check} The original documentation is authoritative; follow the citation links before relying on a detail.</p></footer>
<script>
{js}
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description="Render a tldr bundle (pages/*.md) into one HTML file.")
    ap.add_argument("bundle", help="bundle directory containing pages/ and src/")
    ap.add_argument("-o", "--out", help="output file (default: <bundle>/index.html)")
    a = ap.parse_args()
    root = Path(a.bundle)
    if not list((root / "pages").glob("*.md")):
        sys.exit(f"ERROR no pages/*.md in {root}")
    b = Bundle(root)
    out = Path(a.out) if a.out else root / "index.html"
    out.write_text(document(b), encoding="utf-8")
    for level, where, msg in LOG.items:
        print(f"{level:5} {where}: {msg}")
    q, v = sum(p.quotes for p in b.order), sum(p.verified for p in b.order)
    print(f"Wrote {out}: {len(b.order)} page(s), {sum(p.minutes for p in b.rest) or sum(p.minutes for p in b.order)} min, "
          f"{q} quotes ({v} verified), {LOG.count('ERROR')} errors, {LOG.count('WARN')} warnings")
    sys.exit(1 if LOG.count("ERROR") else 0)


if __name__ == "__main__":
    main()
