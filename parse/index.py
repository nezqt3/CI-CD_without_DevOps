from parse_python.autogen_env import parse_github_url, get_dependencies, write_env_yml
from parse_javascript.parser_javascript import ParserJavaScript
from parse_java.parser_java import ParserJava
from parse_go.autogen_env_go import parse_github_url, get_go_dependencies, write_go_mod, generate_gitlab_ci
import os
import sys
import argparse
from get_using_languages import Language

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# добавляем папку в sys.path
sys.path.insert(0, parent_dir)
from enums.languages import Languages

class Main:
    def __init__(self, path):
        self.path = path
        self.language = Language(path=path).get_main_language()
        
    def launch_project(self):
        if self.language == Languages.JAVASCRIPT.value:
            parser_java_script = ParserJavaScript(path=self.path)
            data = parser_java_script.parse_repo()
            parser_java_script.save_to_yaml(data)
            parser_java_script.generate_gitlab_ci(data)
        elif self.language == Languages.JAVA.value:
            parser_java = ParserJava(path=self.path)
            data = parser_java.parse_repo()
            parser_java.save_yaml(data)
            parser_java.save_gitlab_ci(data)
        elif self.language == Languages.PYTHON.value:
            owner, repo = parse_github_url(self.path)
            print(f"→ Получение SBOM из GitHub для: {owner}/{repo} ...")
            deps = get_dependencies(owner, repo)
            write_env_yml(deps)
        elif self.language == Languages.GO.value:
            owner, repo = parse_github_url(self.path)
            print(f"→ Получение SBOM из GitHub для: {owner}/{repo} ...")
            deps = get_go_dependencies(owner, repo)
            write_go_mod(deps, owner, repo)
            generate_gitlab_ci()
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Parse a GitHub repository and generate CI/CD files")
    parser.add_argument("--repo", type=str, required=True, help="GitHub repository URL")
    args = parser.parse_args()
    path = args.repo
    print(path)
    
    main = Main(path)
    main.launch_project()