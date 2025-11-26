#!/usr/bin/env python3
import os
import subprocess
import tempfile
import shutil
import re
import stat
from pathlib import Path
import yaml

def remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)

def clone_repository(repo_url):
    temp_dir = tempfile.mkdtemp()
    try:
        print(f"Клонирование репозитория в {temp_dir}...")
        result = subprocess.run(['git', 'clone', '--depth', '1', repo_url, temp_dir],
                                check=True, capture_output=True, text=True, timeout=60)
        return temp_dir
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"Ошибка клонирования репозитория: {e}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, onerror=remove_readonly)
        return None

def analyze_go_mod(repo_dir):
    go_mod_path = Path(repo_dir) / "go.mod"
    dependencies = []
    if go_mod_path.exists():
        print("Найден go.mod файл")
        try:
            content = go_mod_path.read_text(encoding='utf-8')
            require_section = re.findall(r'require\s+\(([^)]+)\)', content, re.DOTALL)
            if require_section:
                deps = re.findall(r'([^\s]+)\s+([^\s\n]+)', require_section[0])
                dependencies = [f"{dep[0]} {dep[1]}" for dep in deps]
            else:
                deps = re.findall(r'require\s+([^\s]+)\s+([^\s\n]+)', content)
                dependencies = [f"{dep[0]} {dep[1]}" for dep in deps]
        except Exception as e:
            print(f"Ошибка чтения go.mod: {e}")
    else:
        print("go.mod файл не найден")
    return dependencies

def extract_dependencies_from_code(repo_dir):
    dependencies = set()
    repo_path = Path(repo_dir)
    ignore_dirs = {'.git', 'vendor', '.github'}
    go_files = []
    for go_file in repo_path.rglob("*.go"):
        if not any(ignore_dir in go_file.parts for ignore_dir in ignore_dirs):
            go_files.append(go_file)
    print(f"Анализ {len(go_files)} Go файлов...")
    for go_file in go_files:
        try:
            content = go_file.read_text(encoding='utf-8')
            imports = re.findall(r'import\s+\(([^)]+)\)', content, re.DOTALL)
            if imports:
                import_lines = re.findall(r'"[^"]+"', imports[0])
                for imp in import_lines:
                    dep = imp.strip('"')
                    if not dep.startswith(('./', '../')) and len(dep) > 0:
                        dependencies.add(dep)
            single_imports = re.findall(r'import\s+"([^"]+)"', content)
            for imp in single_imports:
                if not imp.startswith(('./', '../')) and len(imp) > 0:
                    dependencies.add(imp)
        except Exception as e:
            print(f"Ошибка чтения файла {go_file}: {e}")
            continue
    return list(dependencies)

def create_dependencies_yaml(go_mod_deps, code_deps):
    all_dependencies = list(set(go_mod_deps + code_deps))
    all_dependencies.sort()
    standard_library = []
    third_party = []
    for dep in all_dependencies:
        if ('.' not in dep.split()[0] or
                dep.startswith('golang.org/x/') or
                dep.split()[0] in ['bufio', 'bytes', 'context', 'encoding/json', 'fmt', 'io', 'net/http', 'os',
                                   'strings', 'time']):
            standard_library.append(dep)
        else:
            third_party.append(dep)
    yaml_data = {
        'project_analysis': {
            'has_go_mod': len(go_mod_deps) > 0,
            'total_dependencies': len(all_dependencies),
            'dependencies_from_go_mod': len(go_mod_deps),
            'dependencies_from_code': len(code_deps),
            'standard_library_deps': len(standard_library),
            'third_party_deps': len(third_party)
        },
        'dependencies': {
            'all': all_dependencies,
            'standard_library': standard_library,
            'third_party': third_party
        }
    }
    return yaml_data

def main():
    repo_url = input("Введите URL Git репозитория: ").strip()
    if not repo_url:
        print("URL репозитория не может быть пустым")
        return
    repo_dir = clone_repository(repo_url)
    if not repo_dir:
        return
    try:
        print("Анализ зависимостей Go проекта...")
        go_mod_deps = analyze_go_mod(repo_dir)
        print(f"Найдено зависимостей в go.mod: {len(go_mod_deps)}")
        code_deps = extract_dependencies_from_code(repo_dir)
        print(f"Найдено зависимостей в коде: {len(code_deps)}")
        yaml_data = create_dependencies_yaml(go_mod_deps, code_deps)
        output_file = "dependencies.yaml"
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True, indent=2)
        print(f"YAML файл создан: {output_file}")
        print(f"Всего зависимостей: {yaml_data['project_analysis']['total_dependencies']}")
        print(f"Стандартная библиотека: {yaml_data['project_analysis']['standard_library_deps']}")
        print(f"Сторонние зависимости: {yaml_data['project_analysis']['third_party_deps']}")
        print("Примеры зависимостей:")
        print("Стандартная библиотека:")
        for i, dep in enumerate(yaml_data['dependencies']['standard_library'][:5], 1):
            print(f"  {i}. {dep}")
        print("Сторонние зависимости:")
        for i, dep in enumerate(yaml_data['dependencies']['third_party'][:5], 1):
            print(f"  {i}. {dep}")
    finally:
        if os.path.exists(repo_dir):
            print(f"Очистка временных файлов...")
            try:
                shutil.rmtree(repo_dir, onerror=remove_readonly)
                print("Временные файлы удалены")
            except Exception as e:
                print(f"Не удалось полностью очистить временные файлы: {e}")

if __name__ == "__main__":
    main()
