from parse_python.parser_python import ParserPython
from parse_javascript.parser_javascript import ParserJavaScript
from parse_java.parser_java import ParserJava
from get_using_languages import Language

path = "https://github.com/nezqt3/VirtualAssistentRZD"
path_js = "https://github.com/nezqt3/Scentury"
path_java = "https://github.com/apache/kafka"

language = Language(path=path_java).get_main_language()

if language == 'JavaScript':
    parser_java_script = ParserJavaScript(path=path_js)
    data = parser_java_script.parse_repo()
    parser_java_script.save_to_yaml(data)
elif language == "Java":
    parser_java = ParserJava(path=path_java)
    data = parser_java.parse_repo()
    parser_java.save_yaml(data)
    parser_java.save_gitlab_ci(data)