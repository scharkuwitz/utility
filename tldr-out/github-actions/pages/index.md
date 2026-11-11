---
title: GitHub Actions, from CI/CD basics to PR audits
source: https://docs.github.com/en/actions
fetched: 2026-11-11
order: ci-cd, github-actions, workflows, python-typescript, pr-auditing, security
---

These pages condense about 7,000 lines of GitHub's documentation on **GitHub Actions**, its CI/CD guides, and its code security features into about 50 minutes of reading. They are written for a developer who knows Git, GitHub pull requests, and Python or TypeScript, but has never set up continuous integration. The first page explains CI/CD itself; the rest build up to automated audits of a codebase and its pull requests.

When you finish, you should be able to write a workflow that lints and tests a Python or TypeScript project on every pull request, add audit jobs that annotate risky lines and block vulnerable dependencies, and avoid the mistakes that let a pull request steal a repository's secrets.

:::background What to know first
You need a GitHub repository you can push to, and a working test command for your project (`pytest`, `npm test`). Workflows are written in YAML; [Writing workflows](workflows.md) has a one-paragraph YAML primer. Every example runs on GitHub-hosted runners; nothing needs a server of your own.
:::

## How the pieces fit

```nest What runs where: one repository, several workflow files, each with jobs on separate machines
Repository : `.github/workflows/`
  `ci.yml` : on push and pull_request
    lint job : runner 1
    test job × 3 : runners 2-4
  `pr-audit.yml` : on pull_request
    diff audit : runner 5
    dependency review : runner 6
```

## Reading paths

- **Never touched CI (50 minutes)**: all pages in order.
- **Get CI running today (15 minutes)**: [How GitHub Actions works](github-actions.md) by example, then [CI for Python and TypeScript](python-typescript.md). Copy a file, change the commands, push.
- **Add PR audits to an existing CI (20 minutes)**: [Auditing code and pull requests](pr-auditing.md), then [Workflow security](security.md). Read the security page before using any trigger other than `pull_request`.

:::pages
:::

## Sources

Condensed from GitHub Docs on 2026-11-11: the Actions get-started pages (overview, quickstart, continuous integration, continuous deployment), the workflow syntax, events and workflow commands references, the Python and Node.js tutorials, the `GITHUB_TOKEN` tutorial, the secure use reference, and the code scanning and dependency review concept pages. The Python and TypeScript audit scripts on the auditing page were written for this bundle and run locally; the workflow files were not run on GitHub.
