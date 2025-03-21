import re
import sys

from src.parser.helper_classes.context import Context
import src.parser.rule_parsing as rule_parsing

class DirectiveFactory:

    @classmethod
    def create(cls, location, virtual_host, if_level, context, node_id, type, conditions, args):
        if type.lower() == 'secruleremovebytag':
            return SecRuleRemoveByTag(location, virtual_host, if_level, context, node_id, type, conditions, args)
        elif type.lower() == 'secruleremovebyid':
            return SecRuleRemoveById(location, virtual_host, if_level, context, node_id, type, conditions, args)
        elif type.lower() in ["definestr", "setenv"]:
            return DefineStr(location, virtual_host, if_level, context, node_id, type, conditions, args)
        elif type.lower() in ["secrule"]:
            return SecRule(location, virtual_host, if_level, context, node_id, type, conditions, args)
        else:
            return Directive(location, virtual_host, if_level, context, node_id, type, conditions, args)

class Directive:

    def __init__(self, location, virtual_host, if_level, context, node_id, type, conditions, args = ''):
        self.Location = location
        self.VirtualHost = virtual_host
        self.IfLevel = if_level
        self.Context = context.clone()
        self.node_id = node_id
        self.type = type.lower()
        self.conditions = conditions
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

    # def properties(self):
    #     return {
    #         **super().properties(),
    #         'tags_to_remove': self.tags_to_remove
    #     }

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
                
    # def properties(self):
    #     return {
    #         **super().properties(),
    #         'ids_to_remove': self.ids_to_remove,
    #         'ranges_to_remove': self.ranges_to_remove
    #     }

class DefineStr(Directive):

    def __init__(self, location, virtual_host, if_level, context, node_id, type, conditions, args):
        super().__init__(location, virtual_host, if_level, context, node_id, type, conditions, args)
        match_definestr = re.match(r"^\s*(?P<name>.+?)(?:\s+(?P<value>.*))?$", self.args)
        if match_definestr:
            self.cst_name = match_definestr.group('name')
            self.cst_value = match_definestr.group('value')

    # def properties(self):
    #     return {
    #         **super().properties(),
    #         'cst_name': self.cst_name,
    #         'cst_value': self.cst_value
    #     }

def parse_args(type: str, args):
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
    separated_vars, vars_no_value, vars_unset = parse_args('setvar', args)
    vars = {}
    for key in separated_vars:
        splitted = key.split('.')
        if len(splitted) != 2:
            vars[key] = separated_vars[key]
        else:
            vars[splitted[0].upper()] = vars.get(splitted[0].upper(), []) + [(splitted[1], separated_vars[key])]
    collected_vars_no_value = {}
    for var in vars_no_value:
        splitted = var.split('.')
        if len(splitted) != 2:
            collected_vars_no_value[var] = None
        else:
            collected_vars_no_value[splitted[0].upper()] = collected_vars_no_value.get(splitted[0].upper(), set()).union([splitted[1]])
    collected_vars_unset = {}
    for var in vars_unset:
        splitted = var.split('.')
        if len(splitted) != 2:
            collected_vars_unset[var] = None
        else:
            collected_vars_unset[splitted[0].upper()] = collected_vars_unset.get(splitted[0].upper(), set()).union([splitted[1]])
    return vars, collected_vars_no_value, collected_vars_unset

class SecRule(Directive):

    def __init__(self, location, virtual_host, if_level, context, node_id, type, conditions, args=''):
        super().__init__(location, virtual_host, if_level, context, node_id, type, conditions, args)
        parsed = rule_parsing.parse_arguments(self.args)
        if len(parsed) != 2 and len(parsed) != 3:
            raise Exception(f"Invalid SecRule directive: {self.args}")

        # var_pattern = re.compile(r"\|?[!&]{0,2}([^:\s|]+)(?::((?:(?:[\"'])?\/.*\/(?:[\"'])?)|(?:[^|]*)))?")
        var_pattern = re.compile(r"\|?[!&]{0,2}([^:\s|]+)(?::((?:\'.*?\')|(?:\".*?\")|(?:\/.+?\/)|(?:[^|]*)))?")
        self.secrule_vars = re.findall(var_pattern, rule_parsing.strip_quotes(parsed[0]))
        self.num_of_vars = len(self.secrule_vars)
        self.secrule_vars = [rule_parsing.strip_quotes(var) for variables in self.secrule_vars for var in variables]
        # self.secrule_vars = [var[0] if var[1] == '' else ":".join(var) for var in self.secrule_vars]
        # print(self.secrule_vars)

        self.secrule_op = parsed[1]
        if len(parsed) == 3:
            self.secrule_actions = parsed[2].split()

        envs, envs_no_value, unset = parse_args_setenv(self.args)
        self.setenv_vars = [] 
        # for key in envs:
        #     self.setenv_vars.append(key)
        #     for value in envs[key]:
        #         if value:
        #             self.setenv_vars.append(value)
        self.setenv_num_vars = len(envs)
        self.setenv_vars = [e for it in envs.items() for e in it]
        self.setenv_vars_no_value = list(envs_no_value)
        self.setenv_unset = list(unset)

        vars, vars_no_value, vars_unset = parse_args_setvar(self.args)
        # self.setvar_vars = [e for it in vars.items() for e in it]
        self.setvar_vars = []
        for key in vars:
            for value in vars[key]:
                self.setvar_vars.append(key)
                self.setvar_vars.extend(value)
        self.setvar_num_vars = len(self.setvar_vars)//3
        self.setvar_vars_no_value = []
        for key in vars_no_value:
            if vars_no_value[key] is None:
                self.setvar_vars_no_value.append(key)
                self.setvar_vars_no_value.append("")
            else:
                for value in vars_no_value[key]:
                    self.setvar_vars_no_value.append(key)
                    self.setvar_vars_no_value.extend(value)
        self.setvar_num_vars_no_value = len(self.setvar_vars_no_value)//2
        self.setvar_unset = []
        for key in vars_unset:
            if vars_unset[key] is None:
                self.setvar_unset.append(key)
                self.setvar_unset.append("")
            else:
                for value in vars_unset[key]:
                    self.setvar_unset.append(key)
                    self.setvar_unset.append(value)
        self.setvar_num_unset = len(self.setvar_unset)//2
        