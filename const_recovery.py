

import sys
from context import FileContext, MacroContext
from prototype import Directive
import re

CONF_PATH = "conf/"

def convert_context_path( path: str):
    begin_pattern = re.compile(r"^.*conf/")
    return re.sub(begin_pattern, CONF_PATH, path)

def find_line(path:str, line_num:int, target:str = ""):
    starting_line = line_num
    with open(path, 'r') as f:
        lines = f.readlines()
        line= lines[line_num-1]
        if target:
            while not re.match(rf"(?i)\s*(Use)?\s*{target}\s*", line):
            # while not line.strip().lower().startswith(target.lower()):
                line_num += 1
                if line_num > len(lines):
                    # raise Exception(f"Line not found in {path}:{starting_line}, for directive {target}")
                    return ""
                line = lines[line_num - 1]
    return line

def old_recover_used_constants(directive: Directive):
    context = directive.Context
    stack_cont = []
    if isinstance(context, MacroContext):
        stack_cont.append(context.definition)
        while isinstance(context.use,MacroContext):
            context = context.use
            stack_cont.append(context.definition)
        if isinstance(context.use, FileContext):
            stack_cont.append(context.use)
        else:
            raise Exception("Invalid Context")
    else:
        stack_cont.append(context)
    # print(stack_cont)

    print(directive)
    tracked_args = {}
    target = directive.type
    for i in range(len(stack_cont)):
        path = convert_context_path(stack_cont[i].file_path)
        line_num = stack_cont[i].line_num
        if not path or not line_num:
            return [] #TODO should not trigger
        line_def = find_line(path, line_num)
        line_usage = find_line(path, line_num, target)
        if line_def != line_usage:
            print(f"\t{line_def} || {line_usage}")
            # pass
        if isinstance(stack_cont[i], MacroContext):
            target = stack_cont[i].macro_name

    consts = []
    return consts

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
    while isinstance(ctx_ptr, MacroContext):
        def_path = convert_context_path(ctx_ptr.definition.file_path)
        def_line = ctx_ptr.definition.line_num
        # store macro definition
        macro_def[ctx_ptr.macro_name] = parse_macro_def(def_path, def_line)[1]
        target_line = find_line(def_path, def_line, target)
        # heuristic to counter the calling of macros trough other macros
        if target_line == "":
            target_line = find_line(def_path, def_line, "@macro")

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
            if i in macro_tint.get(target, [i]):
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
    if isinstance(ctx_ptr, FileContext):
        target_line = find_line(convert_context_path(ctx_ptr.file_path), ctx_ptr.line_num, target)
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
    # print(macro_def)
    # print(macro_tint)
    # print(constants)
    return constants
    # print("="*20)