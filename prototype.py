import re


class Directive:

    def __init__(self, location, virtual_host, if_level, context, ordering_num, type, conditions, args = ''):
        self.Location = location
        self.VirtualHost = virtual_host
        self.IfLevel = if_level
        self.Context = context.clone()
        self.ordering_num = ordering_num
        self.type = type
        self.conditions = conditions
        self.args = args
        self.constants = []
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
        tags_pattern = re.compile(r'tag\s*:\s*(?P<tag>.*?)[,$]')
        phase_pattern = re.compile(r'phase\s*:\s*(?P<phase>\d+)')
        msg_pattern = re.compile(r'msg\s*:\s*(?P<msg>.*?)[,$]')
        match_id = id_pattern.search(args)
        if match_id:
            self.id = int(match_id.group('id'))
        self.tags = [re.sub(r'(^[\"\'])|([\"\']$)', "", match_tag.group("tag")) for match_tag in tags_pattern.finditer(args)]
        # match_tags = tags_pattern.findall(args)
        # if match_tags:
        #     self.tags = match_tags.group('tags')
        match_phase = phase_pattern.search(args)
        if match_phase:
            self.phase = int(match_phase.group('phase'))
        match_msg = msg_pattern.search(args)
        if match_msg:
            self.msg = match_msg.group('msg')

    def properties(self):
        return {
            'type': self.type,
            'Location': self.Location,
            'VirtualHost': self.VirtualHost,
            'IfLevel': self.IfLevel,
            'Context': self.Context,
            'PrettyContext': self.Context.pretty(),
            'ordering_num': self.ordering_num,
            'conditions': self.conditions,
            'args': self.args,
            'msg': self.msg,
            'constants': self.constants,
            'id': self.id,
            'tags': self.tags,
            'phase': self.phase
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