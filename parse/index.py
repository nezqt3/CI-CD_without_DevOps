from parse_python.parser_python import ParserPython
from parse_javascript.parser_javascript import ParserJavaScript

path = "https://github.com/nezqt3/VirtualAssistentRZD"

parser = ParserPython(path=path)

data = parser.parse_repo()
print(parser.save_to_yaml(data))