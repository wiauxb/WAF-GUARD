
import re


class Macro:

    @classmethod
    def parse_macro_def(cls, path:str, line:int):
        macro_pattern = re.compile(r"\s*<\s*Macro\s+(?P<name>\w+)(?:\s+(?P<args>.*))?\s*>")
        with open(path, 'r') as f:
            lines = f.readlines()
            def_line = lines[line-1]
        match = re.match(macro_pattern, def_line)
        if match:
            return match.group("name"), match.group("args").split() if match.group("args") else []
        else:
            raise Exception(f"Macro definition not found in {path}:{line}")

    @classmethod
    def find_line_inside_macro(cls, path, line_num, offset = 0, target:str = ""):
        with open(path, 'r') as f:
            lines = f.readlines()
            if len(lines) < line_num + offset:
                raise ValueError(f"Line {line_num + offset} does not exist in {path}")
            line= lines[line_num-1]
            while offset > 0:
                line_num += 1
                if line_num > len(lines):
                    # raise Exception(f"Line not found in {path}:{starting_line}, for directive {target}")
                    return ""
                line = lines[line_num - 1]
                if line.strip().startswith("#"):
                    continue
                offset -= 1
            if target:
                while not re.match(rf"(?i)\s*(Use)?\s*{target}\s*", line):
                # while not line.strip().lower().startswith(target.lower()):
                    line_num += 1
                    if line_num > len(lines):
                        # raise Exception(f"Line not found in {path}:{starting_line}, for directive {target}")
                        return ""
                    line = lines[line_num - 1]
        return line