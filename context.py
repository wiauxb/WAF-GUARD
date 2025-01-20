from copy import deepcopy


class Context:
    def __init__(self, line_num : int):
        self.line_num = line_num

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f"line {self.line_num}"

    def clone(self):
        return deepcopy(self)


class FileContext(Context):
    def __init__(self, line_num : int, file_path : str):
        super().__init__(line_num)
        self.file_path = file_path

    def __str__(self):
        return f"{self.file_path}:{self.line_num}"


class MacroContext(Context):
    def __init__(self, macro_name : str, defined_in : FileContext, used_in : Context):
        self.macro_name = macro_name
        self.definition = defined_in
        self.use = used_in

    def __str__(self):
        return f"[{self.macro_name}]({self.definition}) used in {self.use}"