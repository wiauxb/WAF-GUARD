import re


# function parsing the string of the arguments and outputting a list of arguments
# arguments are separated with spaces, but can be enclosed in quotes
def parse_arguments(args: str):
    # split the string by spaces, but keep the quoted strings together
    # e.g. 'a b "c d"' -> ['a', 'b', 'c d']
    return re.findall(r'(?:\"[^\"]*\"|\'[^\']*\'|\S)+', args)

def get_args_from_line(line:str):
    args = parse_arguments(line)
    if len(args) < 2:
        print(f"WARN: Not enough arguments in line: {line}")
        return []
    if args[0].lower() == "use":
        args = args[2:]
    else:
        args = args[1:]
    return args


# strip quotes from a string, only strip quotes if the string starts and ends with the same quote
def strip_quotes(s: str):
    if len(s) < 2:
        return s
    if s[0] == s[-1] and s[0] in ['"', "'"]:
        return s[1:-1]
    return s
