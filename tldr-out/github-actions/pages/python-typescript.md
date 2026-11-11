---
title: CI for Python and TypeScript
source: https://docs.github.com/en/actions/tutorials/build-and-test-code/python
fetched: 2026-11-11
summary: Complete lint-and-test workflows for a Python project and a TypeScript (Node.js) project, with version matrices and caching.
group: Recipes
---

A CI workflow for a Python or TypeScript project has the same four steps: **check out** the code, **install the language** at a pinned version with `actions/setup-python` or `actions/setup-node`, **install dependencies** from the lock file with caching, and **run the same commands you run locally**: lint, type-check, test. GitHub's tutorials put the last point plainly: "You can use the same commands that you use locally to build and test your code."[^same] This page gives a complete file for each language, then the variations people need most.

:::infobox
Python setup: `actions/setup-python@v5`
Node setup: `actions/setup-node@v7`
Python install: `pip install -r requirements.txt`
Node install: `npm ci`
Built-in cache: `cache: pip` / `cache: npm`
Python lint: `ruff check --output-format=github`
TypeScript check: `npx tsc --noEmit`
Sources: [Python tutorial](https://docs.github.com/en/actions/tutorials/build-and-test-code/python), [Node.js tutorial](https://docs.github.com/en/actions/tutorials/build-and-test-code/nodejs)
:::

## Why the setup actions

Runners come with some Python and Node.js preinstalled, but which version you get "varies between GitHub-hosted runners, which may cause unexpected changes or use an older version than expected."[^default-py] The setup actions pin the version: `setup-python` "finds a specific version of Python or PyPy from the tools cache on each runner and adds the necessary binaries to `PATH`", downloading it if missing.[^setup-py] `setup-node` does the same for Node.js.[^setup-node]

Both also cache the package manager's download cache when you pass `cache:`. `setup-python` looks for the dependency file (`requirements.txt`, `Pipfile.lock` or `poetry.lock`) "in the whole repository" to build the cache key.[^cache-key] A changed lock file means a new cache.

```flow One CI job, both languages
Checkout : `actions/checkout`
Setup : `setup-python` / `setup-node` with `cache:`
Install : `pip install -r` / `npm ci`
Lint and type-check : `ruff` / `eslint`, `tsc`
Test : `pytest` / `npm test`
```

## By example

:::example Python: lint, then test on three versions
Lint once; the result doesn't depend on the Python version. `--output-format=github` makes Ruff print each finding in GitHub's annotation format, so it appears on the PR's changed lines. The Ruff step is from GitHub's Python tutorial.[^ruff]

```yaml .github/workflows/python-ci.yml
name: Python CI
on:
  push:
    branches: [main]
  pull_request:
permissions:
  contents: read

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v5
        with:
          python-version: '3.x'
      - run: pipx install ruff
      - run: ruff check --output-format=github
      - run: ruff format --diff
```

Test on each supported version with a matrix. Quote versions: unquoted `3.10` is the number 3.1 in YAML.

```yaml
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
      - run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - run: pytest --junitxml=junit/test-results.xml --cov --cov-report=xml
      - uses: actions/upload-artifact@v4
        if: ${{ always() }}
        with:
          name: pytest-results-${{ matrix.python-version }}
          path: junit/test-results.xml
```

`if: always()` uploads the report even when tests fail, which is when you need it. The artifact name includes the matrix value so the three jobs don't collide.
:::

:::example TypeScript: type-check, lint, test
The Node.js tutorial's template: `npm ci`, then build if a build script exists, then test.[^node-template] `npm ci` "installs the versions in the `package-lock.json` or `npm-shrinkwrap.json` file and prevents updates to the lock file."[^npm-ci]

```yaml .github/workflows/node-ci.yml
name: Node CI
on:
  push:
    branches: [main]
  pull_request:
permissions:
  contents: read

jobs:
  check:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: ['20.x', '22.x', '24.x']
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-node@v7
        with:
          node-version: ${{ matrix.node-version }}
          cache: npm
      - run: npm ci
      - run: npx tsc --noEmit
      - run: npx eslint .
      - run: npm run build --if-present
      - run: npm test
```

`'20.x'` means the latest 20 release: "The 'x' in the version number is a wildcard character that matches the latest minor and patch release available for a version."[^x] For pnpm or Yarn, change `cache:` to `pnpm` or `yarn` and the install command to match.[^yarn]
:::

:::background TypeScript commands used above
`tsc --noEmit` runs the TypeScript compiler as a type checker only: it reports type errors and writes no files. ESLint is the common linter for TypeScript; it needs a config file (`eslint.config.js`) in the repository. Neither is specific to GitHub Actions, and both exit non-zero on errors, which is what fails the step.
:::

:::exercise Add CI to a project you have
1. Pick the Python or Node file above and save it under `.github/workflows/` in a branch of your repository.
2. Replace the lint and test commands with the ones you use locally.
3. Push the branch and open a pull request.

Check: the PR shows one check per matrix job (for example `test (3.12)`), and each passes or fails with the same result as your local run.

Variation: introduce a lint error on purpose. With `--output-format=github`, it appears as an annotation on the changed line in **Files changed**.
:::

:::recipes
- Use the latest Python 3:
  `python-version: '3.x'`

- Install from `requirements.txt` with pip caching:
  ```yaml
  - uses: actions/setup-python@v5
    with: { python-version: '3.12', cache: pip }
  - run: pip install -r requirements.txt
  ```

- Skip one combination in a matrix:
  ```yaml
  exclude:
    - os: windows-latest
      python-version: "3.11"
  ```

- Run tox, letting it use the Python that `setup-python` installed:
  `tox -e py`

- Install exact Node dependencies from the lock file:
  `npm ci`

- Run a build only if `package.json` defines one:
  `npm run build --if-present`

- Keep a report from a failed run:
  ```yaml
  - uses: actions/upload-artifact@v4
    if: ${{ always() }}
    with: { name: report, path: junit/ }
  ```
:::

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `##[error]Version 3.7 with arch x64 not found` | That version isn't available for the runner[^not-found] | Pick a listed version; the error shows the available ones |
| Tests pass in CI on a different Python than you expected | No `setup-python`, so the runner's default was used | Always use `setup-python` |
| `npm ci` fails: lock file out of sync | `package.json` changed without updating `package-lock.json` | Run `npm install` locally and commit the lock file |
| Format check fails the build while you migrate | Formatter not yet applied to the codebase | Temporarily `continue-on-error: true` on that step, as the Python tutorial does[^continue] |
| Cache never hits | No lock file, or it's in a subdirectory the action doesn't find | Commit a lock file; for one in a subdirectory, see the setup action's README on dependency paths |
| Matrix uploads fail with a name conflict | Every job uploads an artifact with the same name | Put `${{ matrix.* }}` in the name |

## Not covered

- Publishing to PyPI or npm: [Publishing Node.js packages](https://docs.github.com/en/actions/tutorials/publish-packages/publish-nodejs-packages) and the [Python tutorial](https://docs.github.com/en/actions/tutorials/build-and-test-code/python#publishing-to-pypi).
- Private npm registries and `.npmrc`: [Node.js tutorial](https://docs.github.com/en/actions/tutorials/build-and-test-code/nodejs#example-using-a-private-registry-and-creating-the-npmrc-file).
- Coverage shown on pull requests: [Setting up code coverage](https://docs.github.com/en/code-security/how-tos/maintain-quality-code/set-up-code-coverage).
- Fine-grained caching with `actions/cache`: [Dependency caching reference](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching).

## Check yourself

:::recall
Why use `setup-python` instead of the `python` already on the runner?
: The preinstalled default differs between runners and can change; `setup-python` pins the version you asked for.[^default-py]
What does `npm ci` do that `npm install` doesn't?
: Installs exactly what the lock file says and refuses to update it.[^npm-ci]
Why is the lint job outside the version matrix?
: Lint results don't depend on the runtime version, so running it once saves time.
What does `cache: pip` key the cache on?
: The dependency file it finds, such as `requirements.txt`; a change to that file gives a new cache.[^cache-key]
Why add `if: always()` to an upload step?
: Without it, the step is skipped after a failed test, which is when you want the report.
:::

[^same]: "You can use the same commands that you use locally to build and test your code." https://docs.github.com/en/actions/tutorials/build-and-test-code/python#testing-your-code
[^default-py]: "The default version of Python varies between GitHub-hosted runners, which may cause unexpected changes or use an older version than expected." https://docs.github.com/en/actions/tutorials/build-and-test-code/python#using-the-default-python-version
[^setup-py]: "This action finds a specific version of Python or PyPy from the tools cache on each runner and adds the necessary binaries to `PATH`" https://docs.github.com/en/actions/tutorials/build-and-test-code/python#specifying-a-python-version
[^setup-node]: "The `setup-node` action takes a Node.js version as an input and configures that version on the runner." https://docs.github.com/en/actions/tutorials/build-and-test-code/nodejs#specifying-the-nodejs-version
[^cache-key]: "By default, the `setup-python` action searches for the dependency file (`requirements.txt` for pip, `Pipfile.lock` for pipenv or `poetry.lock` for poetry) in the whole repository." https://docs.github.com/en/actions/tutorials/build-and-test-code/python#caching-dependencies
[^ruff]: "run: ruff check --output-format=github --target-version=py39" https://docs.github.com/en/actions/tutorials/build-and-test-code/python#using-ruff-to-lint-andor-format-code
[^node-template]: "- run: npm run build --if-present" https://docs.github.com/en/actions/tutorials/build-and-test-code/nodejs#specifying-the-nodejs-version
[^npm-ci]: "This example installs the versions in the `package-lock.json` or `npm-shrinkwrap.json` file and prevents updates to the lock file." https://docs.github.com/en/actions/tutorials/build-and-test-code/nodejs#example-using-npm
[^x]: "The 'x' in the version number is a wildcard character that matches the latest minor and patch release available for a version." https://docs.github.com/en/actions/tutorials/build-and-test-code/nodejs#specifying-the-nodejs-version
[^yarn]: "The following example caches dependencies for pnpm (v6.10+)." https://docs.github.com/en/actions/tutorials/build-and-test-code/nodejs#example-caching-dependencies
[^not-found]: "If you specify a version of Python that is not available, `setup-python` fails with an error such as: `##[error]Version 3.7 with arch x64 not found`." https://docs.github.com/en/actions/tutorials/build-and-test-code/python#excluding-a-version
[^continue]: "The formatting step has `continue-on-error: true` set. This will keep the workflow from failing if the formatting step doesn't succeed." https://docs.github.com/en/actions/tutorials/build-and-test-code/python#using-ruff-to-lint-andor-format-code
