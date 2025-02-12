import re
import sys

class DirectiveFactory:

    @classmethod
    def create(cls, location, virtual_host, if_level, context, ordering_num, type, conditions, args):
        if type.lower() == 'secruleremovebytag':
            return SecRuleRemoveByTag(location, virtual_host, if_level, context, ordering_num, type, conditions, args)
        elif type.lower() == 'secruleremovebyid':
            return SecRuleRemoveById(location, virtual_host, if_level, context, ordering_num, type, conditions, args)
        elif type.lower() in ["definestr", "setenv"]:
            return DefineStr(location, virtual_host, if_level, context, ordering_num, type, conditions, args)
        else:
            return Directive(location, virtual_host, if_level, context, ordering_num, type, conditions, args)

class Directive:

    def __init__(self, location, virtual_host, if_level, context, ordering_num, type, conditions, args = ''):
        self.Location = location
        self.VirtualHost = virtual_host
        self.IfLevel = if_level
        self.Context = context.clone()
        self.ordering_num = ordering_num
        self.type = type.lower()
        self.conditions = conditions
        self.args = args
        self.constants = []
        self.tags_to_remove = []
        self.ids_to_remove = []
        self.ranges_to_remove = []
        self.num_of_ranges = 0
        self.cst_name = None
        self.cst_value = None
        self.id = None
        self.tags = None
        self.phase = None
        self.msg = None
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

    def processs_args(self, args):
        id_pattern = re.compile(r'id\s*:\s*(?P<id>\d+)')
        tags_pattern = re.compile(r'tag\s*:\s*(?P<tag>.*?)(?:,|$)')
        phase_pattern = re.compile(r'phase\s*:\s*(?P<phase>\d+)')
        msg_pattern = re.compile(r'msg\s*:\s*(?P<msg>.*?)[,$]')
        match_id = id_pattern.search(args)
        if match_id:
            self.id = int(match_id.group('id'))
        self.tags = set([re.sub(r'(^[\"\'])|([\"\']$)', "", match_tag.group("tag")) for match_tag in tags_pattern.finditer(args)])
        # match_tags = tags_pattern.findall(args)
        # if match_tags:
        #     self.tags = match_tags.group('tags')
        match_phase = phase_pattern.search(args)
        if match_phase:
            self.phase = int(match_phase.group('phase'))
        match_msg = msg_pattern.search(args)
        if match_msg:
            msg = match_msg.group('msg')
            self.msg = msg if msg else None

    def properties(self):
        return {
            'type': self.type,
            'Location': self.Location,
            'VirtualHost': self.VirtualHost,
            'IfLevel': self.IfLevel,
            'Context': str(self.Context),
            'PrettyContext': self.Context.pretty(),
            'ordering_num': self.ordering_num,
            'conditions': self.conditions,
            'args': self.args,
            'msg': self.msg,
            'constants': self.constants,
            'id': self.id,
            'tags': list(self.tags),
            'phase': self.phase,
            'tags_to_remove': self.tags_to_remove,
            'ids_to_remove': self.ids_to_remove,
            'ranges_to_remove': self.ranges_to_remove,
            'num_of_ranges': self.num_of_ranges,
            'cst_name': self.cst_name,
            'cst_value': self.cst_value
        }

    def __repr__(self):
        return f"Directive(Type={self.type}, Location={self.Location}, VirtualHost={self.VirtualHost}, IfLevel={self.IfLevel}, " \
               f"Context={self.Context}, OrderingNum={self.ordering_num}, Conditions={self.conditions}, Args={self.args}), Constants={self.constants}, id={self.id}, tags={self.tags}, phase={self.phase}"

    def __eq__(self, other):
        return (self.IfLevel, self.VirtualHost, self.Location, self.ordering_num) == (other.IfLevel, other.VirtualHost, other.Location,other.ordering_num)

    def __lt__(self, other):
        # Compare IfLevel first
        #import pdb; pdb.set_trace()
        if self.IfLevel != other.IfLevel:
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
            return self.ordering_num < other.ordering_num

class SecRuleRemoveByTag(Directive):
    def __init__(self, location, virtual_host, if_level, context, ordering_num, type, conditions, args):
        super().__init__(location, virtual_host, if_level, context, ordering_num, type, conditions, args)
        self.tags_to_remove = [re.sub(r"(^[\"\'])|([\"\']$)", "", tag) for tag in re.split(r"[ ,]", self.args)]

    def properties(self):
        return {
            **super().properties(),
            'tags_to_remove': self.tags_to_remove
        }

class SecRuleRemoveById(Directive):

    def __init__(self, location, virtual_host, if_level, context, ordering_num, type, conditions, args):
        super().__init__(location, virtual_host, if_level, context, ordering_num, type, conditions, args)
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
                
    def properties(self):
        return {
            **super().properties(),
            'ids_to_remove': self.ids_to_remove,
            'ranges_to_remove': self.ranges_to_remove
        }

class DefineStr(Directive):

    def __init__(self, location, virtual_host, if_level, context, ordering_num, type, conditions, args):
        super().__init__(location, virtual_host, if_level, context, ordering_num, type, conditions, args)
        match_definestr = re.match(r"^\s*(?P<name>.+?)(?:\s+(?P<value>.*))?$", self.args)
        if match_definestr:
            self.cst_name = match_definestr.group('name')
            self.cst_value = match_definestr.group('value')

    def properties(self):
        return {
            **super().properties(),
            'cst_name': self.cst_name,
            'cst_value': self.cst_value
        }