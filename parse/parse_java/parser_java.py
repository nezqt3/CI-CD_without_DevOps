import os
import yaml
import shutil
import subprocess
from xml.etree import ElementTree

class ParserJava:
    def __init__(self, path: str, temp_folder="repo_tmp"):
        self.repo_url = path
        self.temp_folder = temp_folder
        
    @staticmethod
    def job_name(module):
        name = module.strip(":").replace(":", "_")
        return f"build_{name}"

    # 1. Клонирование репозитория
    def clone_repo(self):
        if os.path.exists(self.temp_folder):
            shutil.rmtree(self.temp_folder)

        print("Клонирую репозиторий...")
        subprocess.run(
            ["git", "clone", "--depth", "1", self.repo_url, self.temp_folder],
            check=True
        )

    # 2. Рекурсивный сбор всех файлов
    def parse_files(self):
        files = {}

        for root, _, filenames in os.walk(self.temp_folder):
            for name in filenames:
                full_path = os.path.join(root, name)
                rel_path = os.path.relpath(full_path, self.temp_folder)

                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        files[rel_path] = f.read()
                except:
                    files[rel_path] = "__BINARY_FILE__"

        return files

    # 3. Извлечение зависимостей из pom.xml
    def extract_maven_deps(self):
        pom_path = os.path.join(self.temp_folder, "pom.xml")
        deps = []

        if not os.path.exists(pom_path):
            return deps

        try:
            tree = ElementTree.parse(pom_path)
            root = tree.getroot()

            ns = {"m": "http://maven.apache.org/POM/4.0.0"}

            for dep in root.findall(".//m:dependency", ns):
                d = {
                    "groupId": None,
                    "artifactId": None,
                    "version": None,
                    "scope": "compile",
                    "optional": False,
                    "exclusions": []
                }

                node = dep.find("m:groupId", ns)
                if node is not None: d["groupId"] = node.text

                node = dep.find("m:artifactId", ns)
                if node is not None: d["artifactId"] = node.text

                node = dep.find("m:version", ns)
                if node is not None: d["version"] = node.text

                node = dep.find("m:scope", ns)
                if node is not None: d["scope"] = node.text

                node = dep.find("m:optional", ns)
                if node is not None: d["optional"] = (node.text == "true")

                for exc in dep.findall("m:exclusions/m:exclusion", ns):
                    e = {
                        "groupId": exc.find("m:groupId", ns).text,
                        "artifactId": exc.find("m:artifactId", ns).text
                    }
                    d["exclusions"].append(e)

                deps.append(d)

        except Exception as e:
            print("Ошибка чтения pom.xml:", e)

        return deps

    # 4. Извлечение зависимостей из Gradle
    def extract_gradle_deps(self):
        gradle_files = []
        for root, _, files in os.walk(self.temp_folder):
            for f in files:
                if f.endswith(".gradle") or f.endswith(".gradle.kts"):
                    gradle_files.append(os.path.join(root, f))

        deps = set()
        for file in gradle_files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        # Ищем реальные зависимости
                        if line.startswith(("implementation", "compileOnly", "api", "testImplementation", "runtimeOnly")):
                            # Извлекаем строки 'group:artifact:version'
                            if '"' in line:
                                dep = line.split('"')[1]
                                if dep and ":" in dep:
                                    deps.add(dep)
                            elif "'" in line:
                                dep = line.split("'")[1]
                                if dep and ":" in dep:
                                    deps.add(dep)
            except:
                continue

        return sorted(deps)

    # 5. Основной метод
    def parse_repo(self):
        self.clone_repo()

        print("Читаю файлы...")
        files = self.parse_files()

        print("Ищу зависимости Maven...")
        maven_deps = self.extract_maven_deps()

        print("Ищу зависимости Gradle...")
        gradle_deps = self.extract_gradle_deps()

        result = {
            "repository": self.repo_url,
            "dependencies": {
                "maven": maven_deps,
                "gradle": gradle_deps
            },
        }

        print("Удаляю локальный репозиторий...")
        shutil.rmtree(self.temp_folder, ignore_errors=True)

        return result

    # 6. Сохранение YAML
    def save_yaml(self, data, output="repo_data.yaml"):
        with open(output, "w", encoding="utf-8") as f:
            yaml.dump(data, f, sort_keys=False, allow_unicode=True)
        print(f"YAML сохранён → {output}")
        
    def save_gitlab_ci(self, data, output='.github/workflows/gitlab-java.yml'):

        gitlab_ci = {
            "stages": ["build", "test", "deploy"],
            "variables": {
                "GRADLE_OPTS": "-Dorg.gradle.daemon=false"
            }
        }

        gradle_modules = [m for m in data.get("dependencies", {}).get("gradle", []) if m.startswith(":")]

        for module in gradle_modules:
            gitlab_ci[self.job_name(module)] = {
                "stage": "build",
                "image": "gradle:8.3-jdk17",
                "script": [
                    f"./gradlew {module}:clean {module}:build --parallel"
                ],
                "artifacts": {
                    "paths": [f"{module[1:]}/build/libs/"],
                    "expire_in": "1 hour"
                }
            }

        if data.get("dependencies", {}).get("maven"):
            gitlab_ci["maven_build"] = {
                "stage": "build",
                "image": "maven:3.9.1-openjdk-17",
                "script": ["mvn clean install -B"],
                "artifacts": {
                    "paths": ["target/"],
                    "expire_in": "1 hour"
                }
            }

        gitlab_ci["run_tests"] = {
            "stage": "test",
            "image": "gradle:8.3-jdk17",
            "script": [
                "./gradlew test --parallel --continue"
            ],
            "artifacts": {
                "when": "always",
                "reports": {
                    "junit": "**/build/test-results/test/*.xml"
                },
                "expire_in": "1 hour"
            },
            "dependencies": [self.job_name(m) for m in gradle_modules]
        }

        gitlab_ci["deploy"] = {
            "stage": "deploy",
            "image": "alpine:latest",
            "script": [
                "echo 'Деплойить сюда можно что угодно, например на staging!'"
            ],
            "only": ["main"]
        }

        # Сохраняем красиво YAML
        with open(output, "w", encoding="utf-8") as f:
            yaml.dump(gitlab_ci, f, sort_keys=False, allow_unicode=True)
