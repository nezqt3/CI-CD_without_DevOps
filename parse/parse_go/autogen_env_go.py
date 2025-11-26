import requests
import sys
import re
from typing import List, Tuple

GITHUB_TOKEN = ""

def parse_github_url(url: str) -> Tuple[str, str]:
    m = re.search(r"github\.com/([^/]+)/([^/]+)", url)
    if not m:
        raise ValueError("URL должен быть вида https://github.com/owner/repo")
    owner = m.group(1)
    repo = m.group(2).replace(".git", "")
    return owner, repo

def _get_headers():
    import os
    token = GITHUB_TOKEN or os.environ.get("GITHUB_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def parse_purl_for_go(purl: str) -> Tuple[str, str]:
    if not purl:
        return None, None
    m = re.match(r"pkg:golang/([^@]+)@(.+)", purl)
    if m:
        module = m.group(1)
        version = m.group(2)
        return module, version
    m2 = re.search(r"(github\.com/[^@]+)@?(.+)?", purl)
    if m2:
        module = m2.group(1)
        version = m2.group(2) or ""
        return module, version
    return None, None

def normalize_version(v: str) -> str:
    if not v:
        return ""
    v = v.strip()
    if not v.startswith("v") and re.match(r"^\d+\.\d+(\.\d+)?", v):
        return "v" + v
    return v

def get_go_dependencies(owner: str, repo: str) -> List[Tuple[str, str]]:
    headers = _get_headers()
    url = f"https://api.github.com/repos/{owner}/{repo}/dependency-graph/sbom"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        raise Exception(f"GitHub API error: {resp.status_code}\n{resp.text}")
    data = resp.json()
    if "sbom" not in data:
        raise Exception("SBOM не найден в ответе GitHub. Проверьте включён ли dependency graph и доступен ли SBOM.")
    sbom = data["sbom"]
    components = sbom.get("components", []) or []
    packages = sbom.get("packages", []) or []
    found = {}
    for comp in components:
        purl = comp.get("purl") or comp.get("name") or ""
        module, version = parse_purl_for_go(purl)
        if module:
            version = normalize_version(version)
            found[module] = found.get(module) or version
    for pkg in packages:
        purl = pkg.get("purl") or pkg.get("name") or ""
        module, version = parse_purl_for_go(purl)
        if module:
            version = normalize_version(version)
            found[module] = found.get(module) or version
    go_deps = []
    for mod, ver in sorted(found.items()):
        if mod.startswith("github.com/") or "/" in mod:  # простая эвристика
            go_deps.append((mod, ver))
    return go_deps


def write_go_mod(deps: List[Tuple[str, str]], owner: str, repo: str, out_file="go.mod", go_version="1.20"):
    module_name = f"github.com/{owner}/{repo}-autogen"
    lines = []
    lines.append(f"module {module_name}\n")
    lines.append(f"go {go_version}\n")
    if deps:
        lines.append("require (\n")
        for mod, ver in deps:
            if not ver:
                ver = "v0.0.0-0"
            lines.append(f"\t{mod} {ver}\n")
        lines.append(")\n")
    with open(out_file, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"[OK] Файл {out_file} создан. Найдено Go-зависимостей: {len(deps)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование:")
        print("  python autogen_go_mod.py https://github.com/owner/repo")
        sys.exit(1)
    repo_url = sys.argv[1]
    owner, repo = parse_github_url(repo_url)
    print(f"→ Получение SBOM из GitHub для: {owner}/{repo} ...")
    deps = get_go_dependencies(owner, repo)
    write_go_mod(deps, owner, repo)
