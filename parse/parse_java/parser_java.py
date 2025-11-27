import os
import yaml
import base64
import requests
from xml.etree import ElementTree
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


class ParserJava:
    def __init__(self, path: str):
        self.repo_url = path.rstrip("/")
        self.token = GITHUB_TOKEN
        self.owner, self.repo = self._parse_repo_url()
        self.api_base = f"https://api.github.com/repos/{self.owner}/{self.repo}"

    # ----------------------------- UTILS -----------------------------

    def _parse_repo_url(self):
        parts = self.repo_url.split("/")
        if len(parts) < 2:
            raise ValueError("Invalid GitHub repository URL")
        return parts[-2], parts[-1]

    def _headers(self):
        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def get_default_branch(self) -> str:
        """Возвращает default ветку репозитория (main/master/trunk/whatever)."""
        resp = requests.get(self.api_base, headers=self._headers())
        resp.raise_for_status()
        return resp.json().get("default_branch", "main")

    def fetch_repo_tree(self):
        """Получает список всех файлов репозитория через GitHub REST API."""
        branch = self.get_default_branch()
        print(f"📌 Default branch: {branch}")

        # Получаем SHA последнего коммита ветки
        branch_resp = requests.get(f"{self.api_base}/branches/{branch}", headers=self._headers())
        branch_resp.raise_for_status()
        commit_sha = branch_resp.json()["commit"]["sha"]

        # Получаем дерево файлов по SHA
        tree_resp = requests.get(f"{self.api_base}/git/trees/{commit_sha}?recursive=1", headers=self._headers())
        tree_resp.raise_for_status()
        tree = tree_resp.json().get("tree", [])
        return [item for item in tree if item["type"] == "blob"]

    def fetch_blob(self, sha: str) -> str:
        """Скачивает файл по SHA через GitHub REST API."""
        resp = requests.get(f"{self.api_base}/git/blobs/{sha}", headers=self._headers())
        resp.raise_for_status()
        data = resp.json()
        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return ""

    # --------------------------- PARSE FILES --------------------------

    def parse_files(self) -> dict:
        """Возвращает словарь файлов {path: content}."""
        print("📄 Получаю список файлов через Git API...")
        blobs = self.fetch_repo_tree()
        print(f"📦 Найдено файлов: {len(blobs)}")

        files = {}
        for item in blobs:
            path = item["path"]
            sha = item["sha"]
            try:
                content = self.fetch_blob(sha)
                files[path] = content
            except Exception:
                files[path] = "__BINARY_FILE__"
        print("✅ Все файлы загружены")
        return files

    # -------------------------- DEPENDENCIES --------------------------

    def extract_maven_deps(self, files: dict) -> list:
        """Извлекает зависимости Maven из pom.xml."""
        deps = []
        pom_content = files.get("pom.xml")
        if not pom_content:
            return deps

        try:
            root = ElementTree.fromstring(pom_content)
            ns = {"m": "http://maven.apache.org/POM/4.0.0"}
            for dep in root.findall(".//m:dependency", ns):
                deps.append({
                    "groupId": dep.findtext("m:groupId", default=None, namespaces=ns),
                    "artifactId": dep.findtext("m:artifactId", default=None, namespaces=ns),
                    "version": dep.findtext("m:version", default=None, namespaces=ns)
                })
        except Exception as e:
            print("Ошибка чтения pom.xml:", e)
        return deps

    def extract_gradle_deps(self, files: dict) -> list:
        """Извлекает зависимости Gradle из .gradle/.gradle.kts файлов."""
        deps = set()
        for path, content in files.items():
            if not path.endswith((".gradle", ".gradle.kts")):
                continue
            for line in content.splitlines():
                line = line.strip()
                if line.startswith(("implementation", "api", "compileOnly", "runtimeOnly", "testImplementation")):
                    if '"' in line:
                        dep = line.split('"')[1]
                        if ":" in dep:
                            deps.add(dep)
                    elif "'" in line:
                        dep = line.split("'")[1]
                        if ":" in dep:
                            deps.add(dep)
        return sorted(deps)

    # --------------------------- MAIN LOGIC ---------------------------

    def parse_repo(self) -> dict:
        print("🚀 Загружаю репозиторий через Git API...")
        files = self.parse_files()

        print("🔍 Ищу зависимости Maven...")
        maven_deps = self.extract_maven_deps(files)

        print("🔍 Ищу зависимости Gradle...")
        gradle_deps = self.extract_gradle_deps(files)

        return {
            "repository": self.repo_url,
            "dependencies": {
                "maven": maven_deps,
                "gradle": gradle_deps
            }
        }

    # ------------------------------ SAVE ------------------------------

    def save_yaml(self, data: dict, output="repo_data.yaml"):
        with open(output, "w", encoding="utf-8") as f:
            yaml.dump(data, f, sort_keys=False, allow_unicode=True)
        print(f"💾 YAML сохранён → {output}")


    def save_gitlab_ci(self, data, output=".gitlab-ci.yml"):
        has_maven = bool(data.get("dependencies", {}).get("maven"))
        has_gradle = bool(data.get("dependencies", {}).get("gradle"))

        # Автоматическое определение типа проекта
        if has_maven:
            build_system = "maven"
        elif has_gradle:
            build_system = "gradle"
        else:
            build_system = "javac"
        
        gitlab_ci = {
            "stages": ["build", "test", "deploy"],
            "variables": {
                "MAVEN_OPTS": "-Dmaven.test.failure.ignore=true",
                "GRADLE_OPTS": "-Dorg.gradle.daemon=false"
            }
        }

        # -----------------------------
        # BUILD JOB
        # -----------------------------
        build_job = {
            "stage": "build"
        }

        if build_system == "maven":
            build_job.update({
                "image": "maven:3.9.1-openjdk-17",
                "script": ["mvn -B clean package"],
                "artifacts": {
                    "paths": ["target/"],
                    "expire_in": "2 hours"
                }
            })

        elif build_system == "gradle":
            build_job.update({
                "image": "gradle:8.3-jdk17",
                "script": ["./gradlew clean build --parallel"],
                "artifacts": {
                    "paths": ["*/build/libs/", "build/libs/"],
                    "expire_in": "2 hours"
                }
            })

        else:  # plain java
            build_job.update({
                "image": "eclipse-temurin:17",
                "script": [
                    "mkdir -p build",
                    "find src -name \"*.java\" > sources.txt",
                    "javac @sources.txt -d build"
                ],
                "artifacts": {
                    "paths": ["build/"],
                    "expire_in": "2 hours"
                }
            })

        gitlab_ci["build"] = build_job

        # -----------------------------
        # TEST JOB
        # -----------------------------
        test_job = {
            "stage": "test"
        }

        if build_system == "maven":
            test_job.update({
                "image": "maven:3.9.1-openjdk-17",
                "script": ["mvn -B test"],
                "artifacts": {
                    "when": "always",
                    "reports": {
                        "junit": "target/surefire-reports/*.xml"
                    },
                    "expire_in": "1 hour"
                }
            })

        elif build_system == "gradle":
            test_job.update({
                "image": "gradle:8.3-jdk17",
                "script": ["./gradlew test --continue --parallel"],
                "artifacts": {
                    "when": "always",
                    "reports": {
                        "junit": "**/build/test-results/test/*.xml"
                    },
                    "expire_in": "1 hour"
                }
            })

        else:  # plain java — нет тестов
            test_job.update({
                "image": "alpine:latest",
                "script": ["echo '⚠ No test runner available for plain Java — skipping'"]
            })

        gitlab_ci["test"] = test_job

        # -----------------------------
        # DEPLOY JOB
        # -----------------------------
        gitlab_ci["deploy"] = {
            "stage": "deploy",
            "image": "alpine:latest",
            "script": ["echo 'Deploy step'"],
            "only": ["main"]
        }

        # -----------------------------
        # SAVE YAML
        # -----------------------------
        with open(output, "w", encoding="utf-8") as f:
            yaml.dump(gitlab_ci, f, sort_keys=False, allow_unicode=True)

        print(f"💾 CI файл создан → {output}")

