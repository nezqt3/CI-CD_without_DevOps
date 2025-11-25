import requests

class Language:
    def __init__(self, path):
        self.path = path
        
        parts = self.path.rstrip("/").split("/")
        owner = parts[-2]
        repo = parts[-1]
        
        self.url = f"https://api.github.com/repos/{owner}/{repo}/languages"
        
    def get_main_language(self):
        response = requests.get(self.url)
        if response.status_code == 200:
            data = response.json()
            if data:
                main_lang = max(data, key=data.get)
                return main_lang
        else:
            print(f"Ошибка API: {response.status_code}")