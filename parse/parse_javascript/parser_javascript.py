import yaml
import requests
import base64
import json

class ParserJavaScript:
    def __init__(self, path: str, token: str = None):
        """
        :param path: Ссылка на репозиторий
        :param token: GitHub Token (очень желателен, чтобы избежать лимитов API и читать приватные репо)
        """
        self.path = path
        parts = path.rstrip("/").split("/")
        self.owner = parts[-2]
        self.repo = parts[-1]
        self.api_base = f"https://api.github.com/repos/{self.owner}/{self.repo}/contents"
        
        self.headers = {}
        if token:
            self.headers["Authorization"] = f"token {token}"

    def _get_file_content(self, url):
        """Скачивает и декодирует содержимое файла."""
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            # GitHub API возвращает контент в base64
            if "content" in data:
                return base64.b64decode(data["content"]).decode('utf-8')
        return None

    def _fetch_root_files(self):
        """Получает список файлов только в корне (для анализа структуры)."""
        response = requests.get(self.api_base, headers=self.headers)
        if response.status_code != 200:
            print(f"Ошибка API: {response.status_code}")
            return []
        return response.json()

    def detect_tech_stack(self, package_json, file_names):
        """Определяет фреймворк и тип приложения."""
        dependencies = {**package_json.get("dependencies", {}), **package_json.get("devDependencies", {})}
        
        stack_info = {
            "framework": "node-unknown",
            "type": "backend", # backend, frontend, fullstack
            "is_docker": "Dockerfile" in file_names
        }

        # Эвристика для определения фреймворка
        if "react" in dependencies:
            stack_info["framework"] = "react"
            stack_info["type"] = "frontend"
            if "next" in dependencies:
                stack_info["framework"] = "nextjs"
                stack_info["type"] = "fullstack"
        elif "vue" in dependencies:
            stack_info["framework"] = "vue"
            stack_info["type"] = "frontend"
            if "nuxt" in dependencies:
                stack_info["framework"] = "nuxtjs"
                stack_info["type"] = "fullstack"
        elif "@angular/core" in dependencies:
            stack_info["framework"] = "angular"
            stack_info["type"] = "frontend"
        elif "@nestjs/core" in dependencies:
            stack_info["framework"] = "nestjs"
            stack_info["type"] = "backend"
        elif "express" in dependencies:
            stack_info["framework"] = "express"
            stack_info["type"] = "backend"

        return stack_info

    def parse_repo(self):
        print(f"Анализ репозитория: {self.owner}/{self.repo} ...")
        
        root_items = self._fetch_root_files()
        file_names = [item["name"] for item in root_items]
        
        # 1. Определение Package Manager
        package_manager = "npm" # default
        install_cmd = "npm install"
        
        if "yarn.lock" in file_names:
            package_manager = "yarn"
            install_cmd = "yarn install"
        elif "pnpm-lock.yaml" in file_names:
            package_manager = "pnpm"
            install_cmd = "pnpm install"

        # 2. Поиск и парсинг package.json
        pkg_json_data = {}
        node_version = "latest" # fallback
        has_build_script = False
        has_test_script = False
        
        package_json_item = next((item for item in root_items if item["name"] == "package.json"), None)
        
        if package_json_item:
            content_str = self._get_file_content(package_json_item["url"])
            if content_str:
                try:
                    pkg_json_data = json.loads(content_str)
                    
                    # Проверяем скрипты
                    scripts = pkg_json_data.get("scripts", {})
                    has_build_script = "build" in scripts
                    has_test_script = "test" in scripts
                    
                    # Проверяем версию Node
                    engines = pkg_json_data.get("engines", {})
                    if "node" in engines:
                        node_version = engines["node"]
                        
                except json.JSONDecodeError:
                    print("Ошибка парсинга package.json")

        # 3. Определение стека технологий
        tech_stack = self.detect_tech_stack(pkg_json_data, file_names)

        # Формируем итоговый объект для генератора CI/CD
        repo_data = {
            "repository_name": self.repo,
            "language": "javascript",
            "detected_stack": tech_stack,
            "ci_config": {
                "package_manager": package_manager,
                "install_command": install_cmd,
                "node_version": node_version,
                "has_build": has_build_script,
                "build_command": f"{package_manager} run build" if has_build_script else None,
                "has_test": has_test_script,
                "test_command": f"{package_manager} run test" if has_test_script else None,
            }
        }
        
        return repo_data

    def save_to_yaml(self, data, output_file="js_repo_analysis.yaml"):
        with open(output_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        print(f"Анализ завершен. Результат в: {output_file}")


if __name__ == "__main__":
    url = "https://github.com/nezqt3/Scentury" 
    parser = ParserJavaScript(url)
    data = parser.parse_repo()
    parser.save_to_yaml(data)