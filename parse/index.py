from parse_python.autogen_env import parse_github_url, get_dependencies, write_env_yml
from parse_javascript.parser_javascript import ParserJavaScript
from parse_java.parser_java import ParserJava
from parse_go.autogen_env_go import parse_github_url, get_go_dependencies, write_go_mod
import sys
import argparse
from get_using_languages import Language

parser = argparse.ArgumentParser(description="Parse a GitHub repository and generate CI/CD files")
parser.add_argument("--repo", type=str, required=True, help="GitHub repository URL")
args = parser.parse_args()

path = list(args._get_kwargs()[0])[1]

language = Language(path=path).get_main_language()

if language == 'JavaScript':
    parser_java_script = ParserJavaScript(path=path)
    data = parser_java_script.parse_repo()
    parser_java_script.save_to_yaml(data)
    parser_java_script.generate_gitlab_ci(data)
elif language == "Java":
    parser_java = ParserJava(path=path)
    data = parser_java.parse_repo()
    parser_java.save_yaml(data)
    parser_java.save_gitlab_ci(data)
elif language == 'Python':
    owner, repo = parse_github_url(path)
    print(f"→ Получение SBOM из GitHub для: {owner}/{repo} ...")
    deps = get_dependencies(owner, repo)
    write_env_yml(deps)
elif language == 'Go':
    owner, repo = parse_github_url(path)
    print(f"→ Получение SBOM из GitHub для: {owner}/{repo} ...")
    deps = get_go_dependencies(owner, repo)
    write_go_mod(deps, owner, repo)