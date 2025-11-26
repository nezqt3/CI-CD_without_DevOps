import os
import yaml
import shutil
import subprocess
from xml.etree import ElementTree


class ParserJava:
    def __init__(self, path: str, temp_folder="repo_tmp"):
        self.repo_url = path
        self.temp_folder = temp_folder

    # -------------------------
    # 1. Клонирование репозитория
    # -------------------------
    def clone_repo(self):
        if os.path.exists(self.temp_folder):
            shutil.rmtree(self.temp_folder)

        print("Клонирую репозиторий...")
        subprocess.run(
            ["git", "clone", "--depth", "1", self.repo_url, self.temp_folder],
            check=True
        )

    # -------------------------
    # 2. Рекурсивный сбор всех файлов
    # -------------------------
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

    # -------------------------
    # 3. Извлечение зависимостей из pom.xml
    # -------------------------
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
                group = dep.find("m:groupId", ns).text if dep.find("m:groupId", ns) is not None else None
                artifact = dep.find("m:artifactId", ns).text if dep.find("m:artifactId", ns) is not None else None
                version = dep.find("m:version", ns).text if dep.find("m:version", ns) is not None else None

                deps.append({
                    "group": group,
                    "artifact": artifact,
                    "version": version
                })

        except Exception as e:
            print("Ошибка чтения pom.xml:", e)

        return deps

    # -------------------------
    # 4. Извлечение зависимостей из Gradle
    # -------------------------
    def extract_gradle_deps(self):
        gradle_files = []

        # ищем build.gradle, build.gradle.kts и любые *.gradle
        for root, _, files in os.walk(self.temp_folder):
            for f in files:
                if f.endswith(".gradle") or f.endswith(".gradle.kts"):
                    gradle_files.append(os.path.join(root, f))

        deps = []
        for file in gradle_files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    text = f.read()

                    # Простейший парсер зависимостей
                    for line in text.splitlines():
                        line = line.strip()

                        if "implementation" in line or "compileOnly" in line or "api" in line:
                            if "\"" in line:
                                dep = line.split("\"")[1]
                                deps.append(dep)
                            elif "'" in line:
                                dep = line.split("'")[1]
                                deps.append(dep)
            except:
                pass

        return deps

    # -------------------------
    # 5. Основной метод
    # -------------------------
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
            "files": files
        }

        print("Удаляю локальный репозиторий...")
        shutil.rmtree(self.temp_folder, ignore_errors=True)

        return result

    # -------------------------
    # 6. Сохранение YAML
    # -------------------------
    def save_yaml(self, data, output="repo_data.yaml"):
        with open(output, "w", encoding="utf-8") as f:
            yaml.dump(data, f, sort_keys=False, allow_unicode=True)
        print(f"YAML сохранён → {output}")
