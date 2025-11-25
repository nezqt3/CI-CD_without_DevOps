import yaml
import requests

class ParserJavaScript:
    def __init__(self, path: str):
        self.path = path
        
        parts = path.rstrip("/").split("/")
        self.owner = parts[-2]
        self.repo = parts[-1]

        self.api_base = f"https://api.github.com/repos/{self.owner}/{self.repo}/contents"
    
    def _fetch_dir(self, url, parent=""):
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Ошибка API: {response.status_code} → {url}")
            return []

        items = response.json()
        files = []

        for item in items:
            if item["type"] == "file":
                files.append({
                    "name": item["name"],
                    "path": f"{parent}{item['name']}",
                    "size_bytes": item.get("size", 0)
                })

            elif item["type"] == "dir":
                files.extend(
                    self._fetch_dir(item["url"], parent=f"{parent}{item['name']}/")
                )

        return files
    
    def parse_repo(self):
        """Главный метод — как в твоём классе ParserPython."""
        repo_data = {
            "repository": self.repo,
            "files": self._fetch_dir(self.api_base)
        }
        return repo_data
    
    def save_to_yaml(self, data, output_file="repo_data.yaml"):
        with open(output_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        print(f"YAML сохранён: {output_file}")