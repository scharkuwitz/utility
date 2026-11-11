#!/usr/bin/env python3
"""Collect what gh-issue needs before drafting an issue, in one call. Stdlib only; needs gh.

Usage:
  issue_context.py [REPO] [--search "terms"] [--template NAME]

REPO is owner/repo or a github.com URL; default is the repository in the current directory.
Prints: repository facts and the viewer's permission, where security reports go, the issue
templates (name, purpose, title prefix, labels) and the template chooser config, labels when the
viewer may apply them, and existing issues matching --search in all states.
--template NAME prints that template in full; use it once a template is chosen.
"""
import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

TRIAGE_UP = {"TRIAGE", "WRITE", "MAINTAIN", "ADMIN"}
SECURITY_PATHS = (".github/SECURITY.md", "SECURITY.md", "docs/SECURITY.md")


def gh(*args):
    p = subprocess.run(["gh", *args], capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr.strip()


def raw(repo, path):
    rc, out, _ = gh("api", f"repos/{repo}/contents/{path}", "-H", "Accept: application/vnd.github.raw")
    return out if rc == 0 else None


def resolve(arg):
    if arg:
        m = re.search(r"github\.com[/:]([^/\s]+)/([^/\s#?]+)", arg)
        return f"{m.group(1)}/{m.group(2).removesuffix('.git')}" if m else arg.strip("/")
    rc, out, err = gh("repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner")
    if rc:
        sys.exit(f"!! no repository given and none found in the current directory: {err}")
    return out.strip()


def front(text):
    """Top-level scalar keys of a .md front matter or .yml issue form (enough for a listing)."""
    keys = {}
    for line in text.splitlines()[:40]:
        m = re.match(r"^(name|about|description|title|labels|type):\s*(.*)$", line)
        if m and m.group(1) not in keys:
            keys[m.group(1)] = m.group(2).strip().strip("'\"")
        elif line.startswith("body:"):
            break
    if keys.get("labels") == "":  # YAML list form: "labels:\n  - bug"
        lst = re.search(r"^labels:\s*\n((?:\s+-\s*.+\n)+)", text, re.M)
        keys["labels"] = ", ".join(re.findall(r"-\s*['\"]?([^'\"\n]+)", lst.group(1))) if lst else ""
    return keys


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("repo", nargs="?")
    ap.add_argument("--search", help="terms to look for among existing issues (all states)")
    ap.add_argument("--template", help="print this issue template in full")
    a = ap.parse_args()
    repo = resolve(a.repo)

    if a.template:
        where, _, name = a.template.rpartition(":")  # "owner/.github:bug.yml" reads an inherited template
        where = where or repo
        name = name if "/" in name else f".github/ISSUE_TEMPLATE/{name}"
        body = raw(where, name)
        sys.exit(print(body, end="") if body is not None else f"!! template not found: {where}/{name}")

    fields = "nameWithOwner,description,defaultBranchRef,viewerPermission,isPrivate,isArchived,hasIssuesEnabled,isFork,parent"
    rc, out, err = gh("repo", "view", repo, "--json", fields)
    if rc:
        sys.exit(f"!! {repo}: {err}  (if this is an auth error, run: gh auth login)")
    info = json.loads(out)
    _, login, _ = gh("api", "user", "--jq", ".login")
    perm = info.get("viewerPermission") or "UNKNOWN"
    parent = info.get("parent")

    print(f"repo: {info['nameWithOwner']}  ({'private' if info['isPrivate'] else 'public'})"
          f"  default branch: {(info.get('defaultBranchRef') or {}).get('name', '?')}")
    print(f"viewer: {login.strip()}  permission: {perm}"
          f"  -> labels/assignees {'allowed' if perm in TRIAGE_UP else 'NOT allowed (omit those flags)'}")
    if info.get("description"):
        print(f"about: {info['description']}")
    if parent:
        print(f"fork of: {parent['owner']['login']}/{parent['name']}  (bugs in upstream code belong there)")
    if info["isArchived"]:
        print("!! archived: issues cannot be created")
    if not info["hasIssuesEnabled"]:
        print("!! issues are disabled on this repository")

    with ThreadPoolExecutor(8) as pool:
        listing = pool.submit(gh, "api", f"repos/{repo}/contents/.github/ISSUE_TEMPLATE")
        legacy = pool.submit(raw, repo, ".github/ISSUE_TEMPLATE.md")
        org = f"{repo.split('/')[0]}/.github"  # owner-wide community health defaults
        sec_where = [(repo, p) for p in SECURITY_PATHS] + [(org, p) for p in SECURITY_PATHS[:2]]
        security = [pool.submit(raw, r, p) for r, p in sec_where]
        labels = pool.submit(gh, "label", "list", "-R", repo, "--limit", "200", "--json", "name,description") \
            if perm in TRIAGE_UP else None
        found = pool.submit(gh, "issue", "list", "-R", repo, "--state", "all", "--limit", "10", "--search", a.search,
                            "--json", "number,title,state,updatedAt,url") if a.search else None

        sec = next((p if r == repo else f"{r}/{p}" for (r, p), f in zip(sec_where, security)
                    if f.result() is not None), None)
        print(f"security policy: {sec}  -> vulnerabilities go there, never in a public issue" if sec
              else "security policy: none found")

        src, (rc, out, _) = repo, listing.result()
        if rc and not legacy.result():  # GitHub falls back to the owner's .github repository
            src, (rc, out, _) = org, gh("api", f"repos/{org}/contents/.github/ISSUE_TEMPLATE")
        entries = [e["name"] for e in json.loads(out)] if rc == 0 else []
        forms = [n for n in entries if re.search(r"\.(md|ya?ml)$", n) and n not in ("config.yml", "config.yaml")]
        bodies = dict(zip(forms, pool.map(lambda n: raw(src, f".github/ISSUE_TEMPLATE/{n}") or "", forms)))
        config = next((raw(src, f".github/ISSUE_TEMPLATE/{n}") for n in entries if n.startswith("config.")), None)

    origin = f"  (inherited from {src}; print one with --template {src}:NAME)" if src != repo and forms else ""
    print(f"\nissue templates: {len(forms) or 'none'}{origin}")
    for n in forms:
        k = front(bodies[n])
        kind = "form" if n.endswith(("yml", "yaml")) else "md"
        what = k.get("about") or k.get("description") or ""
        extra = "".join(f"  {key}: {k[key]!r}" for key in ("title", "labels", "type") if k.get(key))
        print(f"  {n:<32} [{kind}] {k.get('name', '')} - {what[:90]}{extra}")
    if legacy.result():
        print("  .github/ISSUE_TEMPLATE.md (single legacy template)")
    if config:
        print("template chooser config:")
        for line in config.strip().splitlines():
            print(f"  | {line}")

    if labels:
        rc, out, _ = labels.result()
        ls = json.loads(out) if rc == 0 else []
        print(f"\nlabels: {len(ls)}")
        for l in ls:
            print(f"  {l['name']}" + (f" - {l['description'][:70]}" if l.get("description") else ""))

    if found:
        rc, out, err = found.result()
        hits = json.loads(out) if rc == 0 else []
        print(f"\nexisting issues for {a.search!r}: {len(hits) if rc == 0 else 'search failed: ' + err}")
        for i in hits:
            print(f"  #{i['number']:<6} {i['state']:<6} {i['updatedAt'][:10]}  {i['title'][:90]}")


if __name__ == "__main__":
    main()
