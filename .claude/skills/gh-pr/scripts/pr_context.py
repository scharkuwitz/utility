#!/usr/bin/env python3
"""Collect what gh-pr needs before writing a pull request, in one call. Stdlib only; needs git and gh.

Usage:
  pr_context.py [--base BRANCH] [--repo OWNER/REPO]

Run inside the working copy. Prints: branch state (uncommitted files, upstream, unpushed
commits), the target repository (the upstream parent when this is a fork), commits and diffstat
against the base, an existing PR for the branch in any state, issue references in the branch name
and commits, recent merged PR titles (the title convention to copy), the PR template text read from
the base branch, and where CONTRIBUTING and CODEOWNERS live.
"""
import argparse
import json
import re
import subprocess
import sys

TEMPLATE = re.compile(r"^(\.github/|docs/)?(pull_request_template\.md|PULL_REQUEST_TEMPLATE/[^/]+\.md)$", re.I)
CONTRIB = re.compile(r"^(\.github/|docs/)?contributing(\.md|\.rst|\.txt)?$", re.I)
CODEOWNERS = re.compile(r"^(\.github/|docs/)?CODEOWNERS$")
ISSUE_REF = re.compile(r"\b(?:(close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+)?((?:[\w.-]+/[\w.-]+)?#\d+)\b", re.I)
MAX_COMMITS, MAX_STAT, MAX_TEMPLATE = 30, 40, 120


def run(*cmd, check=False):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if check and p.returncode:
        sys.exit(f"!! {' '.join(cmd[:3])}: {p.stderr.strip()}")
    return p.stdout.strip() if p.returncode == 0 else None


def git(*args, check=False):
    return run("git", *args, check=check)


def remote_for(repo):
    """Name of the git remote that points at owner/repo, if any."""
    for line in (git("remote", "-v") or "").splitlines():
        name, url = line.split()[:2]
        if re.search(rf"github\.com[/:]{re.escape(repo)}(\.git)?/?$", url, re.I):
            return name
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", help="target branch (default: target repository's default branch)")
    ap.add_argument("--repo", help="target repository (default: upstream parent for forks, else origin)")
    a = ap.parse_args()

    git("rev-parse", "--git-dir", check=True)
    branch = git("branch", "--show-current") or "(detached HEAD)"
    dirty = (git("status", "--porcelain") or "").splitlines()
    upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")

    out = run("gh", "repo", "view", "--json", "nameWithOwner,defaultBranchRef,viewerPermission,isFork,parent",
              check=True)
    here = json.loads(out)
    parent = here.get("parent")
    target = a.repo or (f"{parent['owner']['login']}/{parent['name']}" if parent else here["nameWithOwner"])
    if target == here["nameWithOwner"]:
        tinfo = here
    else:
        tinfo = json.loads(run("gh", "repo", "view", target, "--json", "nameWithOwner,defaultBranchRef,viewerPermission",
                               check=True))
    base = a.base or tinfo["defaultBranchRef"]["name"]
    remote = remote_for(target)
    if remote:
        ref, src = f"refs/remotes/{remote}/{base}", remote
    elif target == here["nameWithOwner"]:
        ref, src = f"refs/remotes/origin/{base}", "origin"
    else:  # fork without an upstream remote: fetch the target's base into a private ref
        ref, src = f"refs/gh-pr/{base}", f"https://github.com/{target}.git"
    fetched = git("fetch", "--quiet", src, f"+refs/heads/{base}:{ref}") is not None
    ref = ref.removeprefix("refs/remotes/")

    print(f"branch: {branch}  upstream: {upstream or 'none (push with -u)'}  uncommitted files: {len(dirty)}")
    for line in dirty[:15]:
        print(f"  {line}")
    if len(dirty) > 15:
        print(f"  ... {len(dirty) - 15} more")
    if upstream:
        unpushed = git("rev-list", "--count", f"{upstream}..HEAD")
        print(f"unpushed commits: {unpushed}")
    head_owner = here["nameWithOwner"].split("/")[0]
    print(f"working repo: {here['nameWithOwner']}  permission: {here.get('viewerPermission')}"
          + (f"  fork of {target}" if parent and target != here["nameWithOwner"] else ""))
    print(f"target: {target}  base: {base}  (compared with {ref}{'' if fetched else ', FETCH FAILED: may be stale'})"
          f"  permission: {tinfo.get('viewerPermission')}")
    if target != here["nameWithOwner"]:
        print(f"  cross-repo PR: use --repo {target} --head {head_owner}:{branch}")
    if branch == base:
        print(f"!! on the base branch '{base}': create a topic branch before opening a PR")

    log = (git("log", "--no-merges", f"--format=%h %s", f"{ref}..HEAD") or "").splitlines()
    print(f"\ncommits ahead of {ref}: {len(log)}")
    for line in log[:MAX_COMMITS]:
        print(f"  {line}")
    if len(log) > MAX_COMMITS:
        print(f"  ... {len(log) - MAX_COMMITS} more")
    behind = git("rev-list", "--count", f"HEAD..{ref}")
    if behind and behind != "0":
        print(f"behind {ref} by {behind} commits (rebase or merge if the diff below looks wrong)")

    stat = (git("diff", "--stat=100", f"{ref}...HEAD") or "").splitlines()
    if stat:
        print("diffstat (net change vs merge base):")
        for line in stat[:MAX_STAT] + (stat[-1:] if len(stat) > MAX_STAT else []):
            print(f"  {line.strip()}")

    refs = {}
    bodies = git("log", "--format=%B", f"{ref}..HEAD") or ""
    for kw, num in ISSUE_REF.findall(f"{branch}\n{bodies}"):
        refs[num] = refs.get(num) or (kw.lower() if kw else "")
    m = re.search(r"(?:^|[/_-])(\d{2,6})(?:[/_-]|$)", branch)
    if m and f"#{m.group(1)}" not in refs:
        refs[f"#{m.group(1)}"] = "branch name"
    print(f"\nissue refs: " + (", ".join(f"{n} ({k})" if k else n for n, k in refs.items()) or "none"))

    existing = run("gh", "pr", "list", "-R", target, "--state", "all", "--head", branch, "--limit", "5",
                   "--json", "number,state,title,url,baseRefName,headRepositoryOwner")
    prs = [p for p in json.loads(existing or "[]")
           if (p.get("headRepositoryOwner") or {}).get("login", head_owner) == head_owner]
    print("existing PR for this branch: " + ("none" if not prs else ""))
    for p in prs:
        print(f"  #{p['number']} {p['state']} -> {p['baseRefName']}  {p['title'][:80]}  {p['url']}")

    titles = run("gh", "pr", "list", "-R", target, "--state", "merged", "--limit", "8", "--json", "title",
                 "--jq", ".[].title")
    print("recent merged PR titles (copy this convention):" + ("" if titles else " none"))
    for t in (titles or "").splitlines():
        print(f"  {t[:100]}")

    files = (git("ls-tree", "-r", "--name-only", ref) or git("ls-files") or "").splitlines()
    for label, rx in (("CONTRIBUTING", CONTRIB), ("CODEOWNERS", CODEOWNERS)):
        hit = next((f for f in files if rx.search(f)), None)
        print(f"{label}: {hit or 'none'}")
    templates = [f for f in files if TEMPLATE.search(f)]
    if not templates:
        print("PR template: none")
    for t in templates:
        text = (git("show", f"{ref}:{t}") or "").splitlines()
        print(f"\nPR template: {t}  ({len(text)} lines)" + ("  [one of several; pick by purpose]" if len(templates) > 1 else ""))
        for line in text[:MAX_TEMPLATE]:
            print(f"  | {line}")
        if len(text) > MAX_TEMPLATE:
            print(f"  | ... {len(text) - MAX_TEMPLATE} more lines: git show {ref}:{t}")


if __name__ == "__main__":
    main()
