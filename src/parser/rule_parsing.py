import re


# function parsing the string of the arguments and outputting a list of arguments
# arguments are separated with spaces, but can be enclosed in quotes
def parse_arguments(args: str):
    # split the string by spaces, but keep the quoted strings together
    # e.g. 'a b "c d"' -> ['a', 'b', 'c d']
    return re.findall(r'(?:\"[^\"]*\"|\'[^\']*\'|\S)+', args)


# strip quotes from a string, only strip quotes if the string starts and ends with the same quote
def strip_quotes(s: str):
    if len(s) < 2:
        return s
    if s[0] == s[-1] and s[0] in ['"', "'"]:
        return s[1:-1]
    return s
