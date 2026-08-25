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
    def find_line_inside_macro(cls, path, line_num, offset=0):
        with open(path, 'r') as f:
            lines = f.readlines()
            if len(lines) < line_num + offset:
                raise ValueError(f"Line {line_num + offset} does not exist in {path}")

            # Start with the last line of the multiline structure
            line = lines[line_num - 1].strip()
            full_line = line

            # Handle offset: Traverse forward if needed
            while offset > 0:
                line_num += 1
                if line_num > len(lines):
                    return ""
                line = lines[line_num - 1].strip()
                full_line = line
                if line.startswith("#"):  # Skip comments
                    continue

                # Handle multiline: Traverse forward to reconstruct the full directive
                while (line_num < len(lines) and full_line.endswith("\\")):
                    line_num += 1
                    line = lines[line_num - 1].strip()
                    full_line += full_line[:-1] + " " + line # Concatenate the current line with the next part

                offset -= 1

            # Handle multiline: Traverse backward to reconstruct the full directive
            # We suppose here that the upper line is not a comment
            while (line_num > 1 and lines[line_num - 2].strip().endswith("\\")):
                line_num -= 1
                line = lines[line_num - 1].strip()
                full_line = line[:-1] + " " + full_line  # Concatenate the current line with the previous part

        return full_line