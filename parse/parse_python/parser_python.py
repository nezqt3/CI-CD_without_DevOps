import os
import yaml

class ParserPython:
    def __init__(self, path: str):
        self.path = path
    
    def parse_repo(self):
        repo_data = {
            "repository": os.path.basename(self.path),
            "files": []
        }

        for root, dirs, files in os.walk(self.path):
            for file in files:
                full_path = os.path.join(root, file)
                repo_data["files"].append({
                    "name": file,
                    "path": full_path.replace(self.path + "/", ""),
                    "size_bytes": os.path.getsize(full_path)
                })

        return repo_data
    
    def save_to_yaml(self, data, output_file="repo_data.yaml"):
        with open(output_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        print(f"YAML сохранён: {output_file}")