import requests
import base64
import yaml
import os

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

class ParserJava:
    def __init__(self, path: str):
        parts = path.rstrip("/").split("/")
        self.owner = parts[-2]
        self.repo = parts[-1]

        self.api_url = "https://api.github.com/graphql"
        self.headers = {
            "Content-Type": "application/json",
        }

    def _graphql(self, query, variables=None):
        payload = {"query": query, "variables": variables or {}}
        r = requests.post(self.api_url, json=payload, headers=self.headers)
        if r.status_code != 200:
            raise Exception(f"GraphQL error {r.status_code}: {r.text}")
        return r.json()

    def _get_tree(self, branch="main"):
        query = """
        query($owner:String!, $repo:String!, $expr:String!) {
          repository(owner:$owner, name:$repo) {
            object(expression:$expr) {
              ... on Tree {
                entries {
                  name
                  path
                  type
                }
              }
            }
          }
        }
        """
        variables = {
            "owner": self.owner,
            "repo": self.repo,
            "expr": f"{branch}:"
        }
        resp = self._graphql(query, variables)
        return resp["data"]["repository"]["object"]["entries"]

    def _fetch_file(self, path, branch="main"):
        query = """
        query($owner:String!, $repo:String!, $expr:String!) {
          repository(owner:$owner, name:$repo) {
            object(expression:$expr) {
              ... on Blob {
                byteSize
                text
                isBinary
              }
            }
          }
        }
        """
        variables = {
            "owner": self.owner,
            "repo": self.repo,
            "expr": f"{branch}:{path}"
        }
        resp = self._graphql(query, variables)
        obj = resp["data"]["repository"]["object"]

        if not obj:
            return None
        if obj.get("isBinary"):
            return "__BINARY_FILE__"
        return obj.get("text")

    def parse_repo(self, branch="main"):
        print("Скачиваю дерево файлов...")
        entries = self._get_tree(branch)

        files = {}
        stack = entries[:]  # рекурсивное дерево

        while stack:
            item = stack.pop()

            if item["type"] == "blob":
                print("FILE:", item["path"])
                files[item["path"]] = self._fetch_file(item["path"], branch)

            elif item["type"] == "tree":
                # поддиректории достаем доп. запросом
                children = self._get_tree(branch + ":" + item["path"])
                for ch in children:
                    ch["path"] = item["path"] + "/" + ch["name"]
                stack.extend(children)

        return {
            "repository": self.repo,
            "files": files
        }

    def save_to_yaml(self, data, output="repo_data.yaml"):
        with open(output, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        print(f"YAML сохранён → {output}")
