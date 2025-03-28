import sys
from src.parser.helper_classes import modsec
from src.parser.helper_classes.context import FileContext, MacroContext
from src.parser.helper_classes.directives import Directive
import re

from src.parser.rule_parsing import get_args_from_line

def recover_used_constants(directive: Directive):
    constants = set()
    macro_def = {}
    macro_tint = {}
    ctx_ptr = directive.Context
    target = directive.type
    initial_line = True
    while isinstance(ctx_ptr, MacroContext):
        macro_def[ctx_ptr.macro_name] = ctx_ptr.get_signature()[1]

        target_line = ctx_ptr.find_line()
        args_from_target = get_args_from_line(target_line)
        tint_macro_def(args_from_target, ctx_ptr, initial_line, macro_def, macro_tint, target)
        constants.update(extract_constants(args_from_target, macro_tint, target, initial_line))

        target = ctx_ptr.macro_name
        ctx_ptr = ctx_ptr.use
        initial_line = False
    if isinstance(ctx_ptr, FileContext):
        target_line = ctx_ptr.find_line()
        args_from_target = get_args_from_line(target_line)
        constants.update(extract_constants(args_from_target, macro_tint, target, initial_line))
    return constants


def tint_macro_def(args_from_target, ctx_ptr, initial_line, macro_def, macro_tint, target):
    for i, arg in enumerate(args_from_target):
        if i in macro_tint.get(target, []) or initial_line:
            # Tint the constants for the context macro
            vars_to_tint = re.findall(r"[\$\@]\w+", arg)
            for var in vars_to_tint:
                # This skip the @operators from modsecurity rules
                if var in modsec.OPERATORS:
                    continue
                if var in macro_def[ctx_ptr.macro_name]:
                    macro_tint[ctx_ptr.macro_name] = macro_tint.get(ctx_ptr.macro_name, []) + [
                        macro_def[ctx_ptr.macro_name].index(var)]
                else:
                    print(
                        f"Variable {var} not found in {ctx_ptr.macro_name} definition from {ctx_ptr.definition.to_real_path()}:{ctx_ptr.definition.line_num}",
                        file=sys.stderr)


def extract_constants(args_from_target, macro_tint, macro_called, initial_line = False):
    constants = set()
    for i, arg in enumerate(args_from_target):
        if i in macro_tint.get(macro_called, []) or initial_line:
            constants_from_line = re.findall(r"[\~\$]\{(?P<name>.*?)\}", arg)
            envvar_from_line = re.findall(r"\%\{(?P<name>.*?)\}", arg)
            constants.update(constants_from_line)
            constants.update(envvar_from_line)
    return constants