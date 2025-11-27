import requests
import yaml
import sys
import re
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def parse_github_url(url: str):
    match = re.search(r"github\.com/([^/]+)/([^/]+)", url)
    if not match:
        raise ValueError("URL must be in format: https://github.com/user/repo")
    return match.group(1), match.group(2).replace(".git", "")


def is_python_package(name: str) -> bool:
    if "/" in name:
        return False

    if name.startswith("com.github"):
        return False

    js_bad = ["grunt", "eslint", "puppeteer", "qunit", "node"]
    if any(bad in name.lower() for bad in js_bad):
        return False

    return re.match(r"^[a-zA-Z0-9._-]+$", name) is not None


def get_dependencies(owner, repo):
    print(owner, repo)
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    url = f"https://api.github.com/repos/{owner}/{repo}/dependency-graph/sbom"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"GitHub API error: {response.status_code}\n{response.text}")

    data = response.json()

    if "sbom" not in data:
        raise Exception("SBOM не найден. Возможно, dependency graph выключен.")

    sbom = data["sbom"]

    components = sbom.get("components", [])
    packages = sbom.get("packages", [])

    raw_deps = []

    for comp in components:
        name = comp.get("name")
        if name:
            raw_deps.append(name)


    for pkg in packages:
        name = pkg.get("name")
        if name:
            raw_deps.append(name)

    clean = sorted({d for d in raw_deps if is_python_package(d)})

    return clean


def write_env_yml(deps: list, out_file="dependencies/environment.yml"):
    env = {
        "name": "auto_env",
        "dependencies": [
            "python=3.10",
            "pip",
            {"pip": deps}
        ]
    }

    with open(out_file, "w") as f:
        yaml.dump(env, f, sort_keys=False, allow_unicode=True)

    print(f"\n[OK] Файл {out_file} создан.")
    print(f"Найдено Python-зависимостей: {len(deps)}")

def write_gitlab_ci_yml(out_file=".gitlab/workflows/gitlab-ci-py.yml"):
    """
    Создает базовый шаблон GitLab CI/CD для Python-проекта
    с использованием environment.yml (conda) или pip.
    """

    gitlab_ci = {
        "stages": ["setup", "test", "deploy"],
        "variables": {
            "PYTHON_VERSION": "3.10"
        },
        "setup_env": {
            "stage": "setup",
            "image": "python:3.10-slim",
            "before_script": [
                "pip install --upgrade pip",
                "pip install pyyaml"
            ],
            "script": [
                "echo 'Установка зависимостей'",
                "if [ -f dependencies/environment.yml ]; then conda env create -f dependencies/environment.yml; fi",
                "if [ -f requirements.txt ]; then pip install -r requirements.txt; fi"
            ],
            "artifacts": {
                "paths": ["dependencies/environment.yml"]
            }
        },
        "run_tests": {
            "stage": "test",
            "image": "python:3.10-slim",
            "script": [
                "echo 'Запуск тестов'",
                "pytest || true"
            ],
            "dependencies": ["setup_env"]
        },
        "deploy": {
            "stage": "deploy",
            "image": "python:3.10-slim",
            "script": [
                "echo 'Деплой (пример)'"
            ],
            "when": "manual",
            "dependencies": ["run_tests"]
        }
    }

    with open(out_file, "w") as f:
        yaml.dump(gitlab_ci, f, sort_keys=False)

    print(f"[OK] {out_file} создан")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование:")
        print("  python autogen_env.py https://github.com/user/repo")
        sys.exit(1)

    repo_url = sys.argv[1]
    owner, repo = parse_github_url(repo_url)

    print(f"→ Получение SBOM из GitHub для: {owner}/{repo} ...")

    deps = get_dependencies(owner, repo)
    write_env_yml(deps)
