from copy import deepcopy
import os
import re

from .macro import Macro


class Context:
    def __init__(self, line_num : int):
        self.line_num = line_num

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f"line {self.line_num}"

    def clone(self):
        return deepcopy(self)

    def pretty(self):
        return self.__str__()

class FileContext(Context):
    def __init__(self, line_num : int, file_path : str):
        super().__init__(line_num)
        self.file_path = file_path

    def to_real_path(self):
        conf_path = os.path.join(os.environ["CONFIG_ROOT"], "conf", "")
        begin_pattern = re.compile(r"^.*conf[/\\]")
        # Handle both Unix and Windows paths by normalizing slashes
        normalized_file_path = self.file_path.replace('\\', '/')
        result = re.sub(begin_pattern, conf_path.replace('\\', '/'), normalized_file_path)
        # Convert back to OS-specific path separators
        return os.path.normpath(result)

    def __str__(self):
        return f"{self.file_path}:{self.line_num}"
    
    def find_line(self):
        path = self.to_real_path()
        line_num = self.line_num
        return Macro.find_line_inside_macro(path, line_num)


class MacroContext(Context):
    def __init__(self, macro_name : str, defined_in : FileContext, used_in : Context):
        self.macro_name = macro_name
        self.definition = defined_in
        self.use = used_in

    def __str__(self):
        return f"line {self.line_num} of " if self.line_num else "" + f"[{self.macro_name}]({self.definition}) used on line {self.use.line_num} of {self.use}"
    
    def pretty(self):
        return f"\"{self.macro_name}\" : {self.definition.pretty()}\n{self.use.pretty()}"

    def get_signature(self):
        return Macro.parse_macro_def(self.definition.to_real_path(), self.definition.line_num)

    def find_line(self):
        path = self.definition.to_real_path()
        line_num = self.definition.line_num
        offset = self.line_num
        return Macro.find_line_inside_macro(path, line_num, offset)