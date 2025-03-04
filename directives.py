import re
import sys

from context import Context
import rule_parsing

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
        self.secrule_vars = [var for variables in self.secrule_vars for var in variables]
        # self.secrule_vars = [var[0] if var[1] == '' else ":".join(var) for var in self.secrule_vars]
        # print(self.secrule_vars)

        self.secrule_op = parsed[1]
        if len(parsed) == 3:
            self.secrule_actions = parsed[2].split()