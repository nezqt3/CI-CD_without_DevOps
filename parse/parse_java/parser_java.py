import yaml
import requests
import base64

class ParserJava:
    def __init__(self, path: str):
        self.path = path
        
        self.GITHUB_TOKEN = "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"
        parts = path.rstrip("/").split("/")
        self.owner = parts[-2]
        self.repo = parts[-1]

        self.api_base = f"https://api.github.com/repos/{self.owner}/{self.repo}/contents"
        self.headers = {"Authorization": f"Bearer {self.GITHUB_TOKEN}"}
    
    def _fetch_file(self, url):
        data = requests.get(url, headers=self.headers).json()
        raw = base64.b64decode(data["content"])
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return "__BINARY_FILE__"
    
    def _fetch_dir(self, url):
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            print(f"Ошибка API: {response.status_code} → {url}")
            return []

        items = requests.get(url).json()
        files = {}
        
        if not isinstance(items, list):
            print(f"Неожиданные данные от API → {items}")
            return {}

        for item in items:
            if item["type"] == "file":
                files[item["path"]] = self._fetch_file(item["url"])
            elif item["type"] == "dir":
                files.update(self._fetch_dir(item["url"]))
        return files
    
    def parse_repo(self):
        repo_data = {
            "repository": self.repo,
            "files": self._fetch_dir(self.api_base)
        }
        return repo_data
    
    def save_to_yaml(self, data, output_file="repo_data.yaml"):
        with open(output_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        print(f"YAML сохранён: {output_file}")