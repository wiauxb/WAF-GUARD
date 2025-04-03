import re
import sys

from src.parser.helper_classes.context import Context
import src.parser.rule_parsing as rule_parsing

class Directive:

    def __init__(self, location, virtual_host, if_level, context, node_id, type, conditions, args = ''):
        self.Location = location
        self.VirtualHost = virtual_host
        self.IfLevel = if_level
        self.Context = context.clone()
        self.node_id = node_id
        self.type = type.lower()
        self.conditions = conditions.copy()
        self.phase = None
        self.constants = []
        self.variables = []
        self.num_of_variables = 0
        self.args = args
        self.processs_args(args)

    def add_constant(self, constant):
        if isinstance(constant, list):
            self.constants.extend(constant)
        elif isinstance(constant, set):
            self.constants.extend(list(constant))
        elif isinstance(constant, str):
            self.constants.append(constant)
        else:
            raise Exception(f"Invalid constant type {type(constant)} (must be list, set or str)")

    def add_variable(self, variable):
        self.num_of_variables += len(variable)
        if isinstance(variable, list):
            self.variables.extend(variable)
        elif isinstance(variable, set):
            self.variables.extend(list(variable))
        elif isinstance(variable, str):
            self.variables.append(variable)
        else:
            raise Exception(f"Invalid constant type {type(variable)} (must be list, set or str)")


    def processs_args(self, args):
        id_pattern = re.compile(r'id\s*:\s*(?P<id>\d+)')
        tags_pattern = re.compile(r'tag\s*:\s*(?P<tag>.*?)(?:,|$)')
        phase_pattern = re.compile(r'phase\s*:\s*(?P<phase>\d+)')
        msg_pattern = re.compile(r'msg\s*:\s*(?P<msg>.*?)[,$]')
        match_id = id_pattern.search(args)
        if match_id:
            self.id = int(match_id.group('id'))
        self.tags = set([re.sub(r'(^[\"\'])|([\"\']$)', "", match_tag.group("tag")) for match_tag in tags_pattern.finditer(args)])

        match_phase = phase_pattern.search(args)
        if match_phase:
            self.phase = int(match_phase.group('phase'))
        match_msg = msg_pattern.search(args)
        if match_msg:
            msg = match_msg.group('msg')
            self.msg = msg if msg else None

    def properties(self):
        rep = {}
        for key, value in self.__dict__.items():
            if key.startswith('_'):
                continue
            if isinstance(value, set):
                rep[key] = list(value)
            elif isinstance(value, Context):
                rep[key] = str(value)
            else:    
                rep[key] = value
        return rep

    def node_properties(self):
        prop = {
            'node_id': self.node_id,
            'type': self.type,
            'args': self.args,
            'Location': self.Location,
            'VirtualHost': self.VirtualHost,
            'IfLevel': self.IfLevel,
            'conditions': self.conditions,
            'constants': self.constants,
            'variables': self.variables,
            'Context': str(self.Context)
        }
        if hasattr(self, 'id'):
            prop['id'] = self.id
        if hasattr(self, 'tags'):
            prop['tags'] = list(self.tags)
        if hasattr(self, 'phase'):
            prop['phase'] = self.phase
        if hasattr(self, 'msg'):
            prop['msg'] = self.msg
        return prop


    def __repr__(self):
        rep = self.__class__.__name__ + "("
        for key, value in self.properties().items():
            rep += f"{key}={value}, "
        return rep[:-2] + ")"

    def __eq__(self, other):
        return (self.IfLevel, self.VirtualHost, self.Location, self.node_id) == (other.IfLevel, other.VirtualHost, other.Location,other.node_id)

    def __lt__(self, other):
        if self.phase != other.phase:
            return self.phase < other.phase
        # Compare IfLevel first
        elif self.IfLevel != other.IfLevel:
            return self.IfLevel < other.IfLevel
        # Check if one of the Location is empty and the other not
        elif self.Location != other.Location and self.Location and not other.Location:    
            return False
        elif self.Location != other.Location and not self.Location and other.Location:
            return True
        elif self.VirtualHost != other.VirtualHost and self.VirtualHost and not other.VirtualHost:
            return False
        elif self.VirtualHost != other.VirtualHost and not self.VirtualHost and other.VirtualHost:
            return True
        else:
            return self.node_id < other.node_id

class SecRuleRemoveByTag(Directive):
    def __init__(self, location, virtual_host, if_level, context, node_id, type, conditions, args):
        super().__init__(location, virtual_host, if_level, context, node_id, type, conditions, args)
        self.tags_to_remove = [re.sub(r"(^[\"\'])|([\"\']$)", "", tag) for tag in re.split(r"[ ,]", self.args)]

class SecRuleRemoveById(Directive):

    def __init__(self, location, virtual_host, if_level, context, node_id, type, conditions, args):
        super().__init__(location, virtual_host, if_level, context, node_id, type, conditions, args)
        ids_strings = re.split(r"[ ,]", self.args)
        self.ids_to_remove= []
        self.ranges_to_remove = []
        self.num_of_ranges = 0
        for s in ids_strings:
            if s == "":
                continue
            s = re.sub(r"(^[\"\'])|([\"\']$)", "", s)
            if s.isdigit():
                self.ids_to_remove.append(int(s))
            else:
                r = s.split("-")
                if len(r) != 2 or not r[0].isdigit() or not r[1].isdigit() or int(r[0]) >= int(r[1]) or int(r[1]) - int(r[0]) > 2500:
                    print(f"Error parsing {type} directive from {context}: {s} is an invalid range", file=sys.stderr)
                    continue
                self.ranges_to_remove.append(int(r[0]))
                self.ranges_to_remove.append(int(r[1]))
                self.num_of_ranges += 1

class DefineStr(Directive):

    def __init__(self, location, virtual_host, if_level, context, node_id, type, conditions, args):
        super().__init__(location, virtual_host, if_level, context, node_id, type, conditions, args)
        match_definestr = re.match(r"^\s*(?P<name>.+?)(?:\s+(?P<value>.*))?$", self.args)
        if match_definestr:
            self.cst_name = match_definestr.group('name')
            self.cst_value = match_definestr.group('value')

def parse_args(type: str, args):
    """
    Parses a string of arguments based on a specified type (either setenv or setvar) and extracts environment variables.

    Args:
        type (str): The type of argument to parse, either setenv or setvar.
        args (str): The string containing the arguments to parse.

    Returns:
        - envs (dict): A dictionary of environment variables with their corresponding values.
        - envs_no_value (set): A set of environment variables that are specified without values.
        - unset_envs (set): A set of environment variables that are marked for unsetting (prefixed with '!').
    """

    pattern_expression = re.compile(fr"{type}:(?P<expression>(?:'(?P<quotes>[^']*?)')|(?:\"(?P<dquotes>[^\"]*?)\")|(?P<noquotes>.+?))(?:,|$|\"|')")
    envs = {}
    envs_no_value = set()
    unset_envs = set()
    for match in pattern_expression.finditer(args):
        expression = ""
        if match.group('quotes'):
            expression = match.group('quotes')
        elif match.group('dquotes'):
            expression = match.group('dquotes')
        elif match.group('noquotes'):
            expression = match.group('noquotes')
        if expression.startswith('!'):
            unset_envs.add(expression[1:])
        elif '=' in expression:
            splitted = expression.split('=')
            envs[splitted[0]] = splitted[1] # envs.get(match.group('name'), set()).union([match.group('value')])
        else:
            envs_no_value.add(expression)
    return envs, envs_no_value, unset_envs

def parse_args_setenv(args):
    return parse_args('setenv', args)

def parse_args_setvar(args):
    """
    Parses the arguments for the 'setvar' directive and organizes them into structured dictionaries.
    Pre-conditions:
    -  args (str): The string containing the arguments to parse.
    Post-conditions:
    - Returns 3 dictionaries:
        1. `vars`: A dictionary where keys are variable names (or uppercased prefixes for dotted keys),
           and values are a list of tuples (suffix, value).
        2. `collected_vars_no_value`: A dictionary where keys are variable names (or uppercased prefixes for dotted keys),
           and values are a set of suffixes for keys that have no value.
        3. `collected_vars_unset`: A dictionary where keys are variable names (or uppercased prefixes for dotted keys),
           and values are a set of suffixes for keys that are marked as unset.
    """

    separated_vars, vars_no_value, vars_unset = parse_args('setvar', args)
    vars = {}
    for key in separated_vars:
        splitted = key.split('.')
        if len(splitted) != 2:
            vars[None] = vars.get(None, []) + [(key, separated_vars[key])] #[separated_vars[key]] #FIXME this break the hypothesis of key -> tuple of lentgh 2
        else:
            vars[splitted[0].upper()] = vars.get(splitted[0].upper(), []) + [(splitted[1], separated_vars[key])]
    collected_vars_no_value = {}
    for var in vars_no_value:
        splitted = var.split('.')
        if len(splitted) != 2:
            collected_vars_no_value[None] = collected_vars_no_value.get(None, set()).union([var])
        else:
            collected_vars_no_value[splitted[0].upper()] = collected_vars_no_value.get(splitted[0].upper(), set()).union([splitted[1]])
    collected_vars_unset = {}
    for var in vars_unset:
        splitted = var.split('.')
        if len(splitted) != 2:
            collected_vars_unset[None] = collected_vars_no_value.get(None, set()).union([var])
        else:
            collected_vars_unset[splitted[0].upper()] = collected_vars_unset.get(splitted[0].upper(), set()).union([splitted[1]])
    return vars, collected_vars_no_value, collected_vars_unset

class SecRule(Directive):

    def __init__(self, location, virtual_host, if_level, context, node_id, type, conditions, args=''):
        super().__init__(location, virtual_host, if_level, context, node_id, type, conditions, args)
        parsed = rule_parsing.parse_arguments(self.args)
        if len(parsed) != 2 and len(parsed) != 3:
            raise Exception(f"Invalid SecRule directive: {self.args}")

        var_pattern = re.compile(r"\|?[!&]{0,2}([^:\s|]+)(?::((?:\'.*?\')|(?:\".*?\")|(?:\/.+?\/)|(?:[^|]*)))?")
        tmp = re.findall(var_pattern, rule_parsing.strip_quotes(parsed[0]))
        self.num_of_vars = len(tmp)
        self.secrule_vars = []
        for coll, var in tmp:
            self.secrule_vars.append((coll.upper(), var))
        self.secrule_vars = [rule_parsing.strip_quotes(var) for variables in self.secrule_vars for var in variables]

        self.secrule_op = parsed[1]
        if len(parsed) == 3:
            self.secrule_actions = parsed[2].split()

        envs, envs_no_value, unset = parse_args_setenv(self.args)
        self.setenv_vars = [] 
        self.setenv_num_vars = len(envs)
        self.setenv_vars = [e for it in envs.items() for e in it]
        self.setenv_vars_no_value = list(envs_no_value)
        self.setenv_unset = list(unset)

        vars, vars_no_value, vars_unset = parse_args_setvar(self.args)
        self.setvar_vars = []
        for key in vars:
            for value in vars[key]:
                if len(value) != 2:
                    print(f"Error parsing {type} directive {node_id} from {context}: {value} is an invalid value", file=sys.stderr)
                    continue
                self.setvar_vars.append(key)
                self.setvar_vars.extend(value)
        self.setvar_num_vars = len(self.setvar_vars)//3
        self.setvar_vars_no_value = []
        for key in vars_no_value:
            for value in vars_no_value[key]:
                self.setvar_vars_no_value.append(key)
                self.setvar_vars_no_value.append(value)
        self.setvar_num_vars_no_value = len(self.setvar_vars_no_value)//2
        self.setvar_unset = []
        for key in vars_unset:
            for value in vars_unset[key]:
                self.setvar_unset.append(key)
                self.setvar_unset.append(value)
        self.setvar_num_unset = len(self.setvar_unset)//2
        