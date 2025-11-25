from parse_python.parser_python import ParserPython
from parse_javascript.parser_javascript import ParserJavaScript
from parse_java.parser_java import ParserJava
from get_using_languages import Language

path = "https://github.com/nezqt3/VirtualAssistentRZD"
path_java = "https://github.com/nezqt3/cryptoAnalyzer"

parser = ParserPython(path=path)
parser_java = ParserJava(path=path_java)

language = Language(path=path_java)

print(language.get_main_language())

data = parser_java.parse_repo()
print(parser_java.save_to_yaml(data))