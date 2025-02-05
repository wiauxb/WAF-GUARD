

import sys
from context import FileContext, MacroContext
from prototype import Directive
import re

CONF_PATH = "conf/"

def convert_context_path( path: str):
    begin_pattern = re.compile(r"^.*conf/")
    return re.sub(begin_pattern, CONF_PATH, path)

def find_line_inside_macro(path:str, line_num:int, offset:int = 0, target:str = ""):
    starting_line = line_num
    with open(path, 'r') as f:
        lines = f.readlines()
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

def parse_macro_def(path:str, line:str):
    macro_pattern = re.compile(r"\s*<\s*Macro\s+(?P<name>\w+)(?:\s+(?P<args>.*))?\s*>")
    with open(path, 'r') as f:
        lines = f.readlines()
        def_line = lines[line-1]
    match = re.match(macro_pattern, def_line)
    if match:
        return match.group("name"), match.group("args").split() if match.group("args") else []
    else:
        raise Exception(f"Macro definition not found in {path}:{line}")

def recover_used_constants(directive: Directive):
    rule_elem_pattern = re.compile(r"(?:\"([^\"]+)\"|\'([^\']+)\'|(\S+))")
    constants = set()
    macro_def = {}
    macro_tint = {}
    ctx_ptr = directive.Context
    target = directive.type
    initial_line = True
    while isinstance(ctx_ptr, MacroContext):
        def_path = convert_context_path(ctx_ptr.definition.file_path)
        def_line = ctx_ptr.definition.line_num
        # store macro definition
        macro_def[ctx_ptr.macro_name] = parse_macro_def(def_path, def_line)[1]
        target_line = find_line_inside_macro(def_path, def_line, ctx_ptr.line_num)

        args_from_target = []
        seen_target = False
        for match in re.finditer(rule_elem_pattern, target_line):
            for group in match.groups():
                if group:
                    if seen_target:
                        args_from_target.append(group)
                    if group.lower() == target.lower() or group.lower() == "@macro": # heuristic to counter the calling of macros trough other macros
                        seen_target = True

        for i, arg in enumerate(args_from_target):
            if i in macro_tint.get(target, []) or initial_line:
                # Tint the constants for the context macro
                vars_to_tint =  re.findall(r"[\$\@]\w+", arg)
                for var in vars_to_tint:
                    # This skip the @operators from modsecurity rules
                    if var in macro_def[ctx_ptr.macro_name]:
                        macro_tint[ctx_ptr.macro_name] = macro_tint.get(ctx_ptr.macro_name, []) + [macro_def[ctx_ptr.macro_name].index(var)]
                    # else:
                    #     print(f"Variable {var} not found in {ctx_ptr.macro_name} definition from {def_path}:{def_line}", file=sys.stderr)
                
                # Extract constants from the arguments
                constants_from_line = re.findall(r"[\~\$]\{(?P<name>.*?)\}", arg)
                envvar_from_line = re.findall(r"\%\{(?P<name>.*?)\}", arg)
                constants.update(constants_from_line)
                constants.update(envvar_from_line)

        target = ctx_ptr.macro_name
        ctx_ptr = ctx_ptr.use
        initial_line = False
    if isinstance(ctx_ptr, FileContext):
        target_line = find_line_inside_macro(convert_context_path(ctx_ptr.file_path), ctx_ptr.line_num)
        args_from_target = []
        seen_target = False
        for match in re.finditer(rule_elem_pattern, target_line):
            for group in match.groups():
                if group:
                    if seen_target:
                        args_from_target.append(group)
                    if group.lower() == target.lower():
                        seen_target = True
        for i, arg in enumerate(args_from_target):
            if i in macro_tint.get(target, []):
                constants_from_line = re.findall(r"[\~\$]\{(?P<name>.*?)\}", arg)
                envvar_from_line = re.findall(r"\%\{(?P<name>.*?)\}", arg)
                constants.update(constants_from_line)
                constants.update(envvar_from_line)
        initial_line = False
    # print(macro_def)
    # print(macro_tint)
    # print(constants)
    return constants
    # print("="*20)