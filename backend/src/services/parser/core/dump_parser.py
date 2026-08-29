import re

from .context import *
from .directive_factory import DirectiveFactory


def parse_compiled_config(file_path, config_root):
    """Parse an Apache dump into Directive objects.

    Args:
        file_path: path to dump.conf
        config_root: directory containing the extracted `conf/` tree, used to map
            dump paths back to real files. PORT CHANGE: was os.environ["CONFIG_ROOT"].
    """
    directives = []

    # Regular expressions for extracting relevant information
    # server_name_pattern = re.compile(r'[ \t]*SetEnv (\S+)')
    modsecrule_pattern = re.compile(r'\s*SecRule\s+(.*)')
    generic_rule_pattern = re.compile(r'\s*(?P<name>\w+)\s+(?P<args>.*)')
    virtual_host_pattern = re.compile(r'<VirtualHost\s+(.*?)>')
    virtual_host_end_pattern = re.compile(r'</VirtualHost>')
    # Both container kinds, captured as (kind, value).
    #
    # `<LocationMatch ...>` used to be invisible here -- after `<Location` comes `Match`,
    # not whitespace -- which left 50,241 directives (54% of this configuration) recorded
    # as applying to no location at all. See PARSER.md defect #1.
    #
    # A single string is enough, no stack: location containers are never nested in a
    # compiled dump (measured ancestor depth is only ever 0 or 1). That also absorbs the
    # 7 EMPTY <LocationMatch> blocks whose `</LocationMatch>` the dump omits entirely --
    # the next open simply overwrites the value, and no directives sit in between. A stack
    # would instead leak the unclosed location onto everything downstream.
    #
    # <Directory>/<DirectoryMatch>/<Proxy> stay out on purpose: those are filesystem
    # paths, a different namespace from the URL paths this field holds.
    location_pattern = re.compile(r'[ \t]*<(Location|LocationMatch)\s+(.*?)>', re.I)
    location_end_pattern = re.compile(r'[ \t]*</(Location|LocationMatch)>', re.I)
    if_pattern = re.compile(r'[ \t]*<If\s+(.*?)>')
    if_pattern_end = re.compile(r'[ \t]*</If>')
    file_flag = re.compile(r'# In file:\s+(.*)')
    context_regex = re.compile(r'(?:macro \'(.*?)\' \(defined on line (\d+) of "(.*?)"\) used on line (\d+) of "(?P<recursion>.*)")|(?:"?(?P<file_path>\/.*)"?)')
    instruction_number_pattern = re.compile(r'\s*#\s+(\d+):')

    with open(file_path, 'r') as file:
        lines = file.readlines()

    current_virtualhost = ""
    current_location = ""
    # "" outside any container, else "Location" or "LocationMatch". A <Location> value is a
    # literal path, a <LocationMatch> value is a regex -- the two are not interchangeable,
    # so which one produced the value has to travel with it.
    current_location_kind = ""
    current_if_level = 0
    current_node_id = 0
    current_context = None
    current_if_conditions = []

    for dump_line_num, line in enumerate(lines):

        # Extract VirtualHost
        match_virtual_host = virtual_host_pattern.match(line)
        if match_virtual_host:
            current_virtualhost = match_virtual_host.group(1)
            current_location = ""
            current_location_kind = ""
            current_if_level = 0 #FIXME: why do I reset the if level here?
            current_if_conditions = []
            continue

        # End VirtualHost
        match_virtual_host_end = virtual_host_end_pattern.match(line)
        if match_virtual_host_end:
            current_virtualhost = ""#match_virtual_host.group(1)
            # Also clear the location: a container cannot outlive its VirtualHost, and only
            # the OPEN used to reset this.
            current_location = ""
            current_location_kind = ""
            continue

        # Extract Location / LocationMatch
        match_location = location_pattern.match(line)
        if match_location:
            # Normalised, so the stored kind never varies with how the dump cased it.
            current_location_kind = (
                "LocationMatch"
                if match_location.group(1).lower() == "locationmatch"
                else "Location"
            )
            # NOT stripped, matching what the <Location> path has always stored.
            current_location = match_location.group(2)
            continue

        # End Location / LocationMatch
        match_location_end = location_end_pattern.match(line)
        if match_location_end:
            current_location = ""
            current_location_kind = ""
            continue

        # Determine if level
        match_if = if_pattern.match(line)
        if match_if:
            current_if_level += 1
            current_if_conditions.append(match_if.group(1))
        if if_pattern_end.match(line):
            current_if_level -= 1
            current_if_conditions.pop()

        tmp_context = []
        match_file_flag =  file_flag.match(line)
        if match_file_flag:
            # current_instruction_number = line_numbers_regex.findall(line)
            # current_macro_stack = macro_names_regex.findall(line) 
            tmp = match_file_flag.group(1)
            while tmp and tmp != "":
                infos = context_regex.match(tmp)
                if infos.group('file_path'):
                    file_ctx = FileContext(None, infos.group('file_path'), config_root)
                    tmp_context.append(file_ctx)
                    break
                else:
                    defined_in = FileContext(int(infos.groups()[1]), infos.groups()[2], config_root)
                    used_in = Context(int(infos.groups()[3]))
                    new_macro = MacroContext(infos.groups()[0], defined_in, used_in)
                    tmp_context.append(new_macro)
                    tmp = infos.group('recursion')
            pred = tmp_context[-1]
            for i in range(len(tmp_context)-2, -1, -1):
                if isinstance(tmp_context[i], MacroContext):
                    pred.line_num = tmp_context[i].use.line_num
                    tmp_context[i].use = pred
                    pred = tmp_context[i]
                else:
                    break
            current_context = tmp_context[0]

        # Extract instruction number
        match_instruction_number = instruction_number_pattern.match(line)
        if match_instruction_number:
            line_num = int(match_instruction_number.group(1))    
            current_context.line_num = line_num

        match_modsecrule = modsecrule_pattern.match(line)
        if match_modsecrule:
            current_node_id = current_node_id+1
            new_directive = DirectiveFactory.create(current_location, current_virtualhost, current_if_level, current_context, current_node_id,"SecRule", current_if_conditions, match_modsecrule.group(1), current_location_kind)
            # print(new_directive)
            directives.append(new_directive)
        else:
            match_generic_rule = generic_rule_pattern.match(line)
            if match_generic_rule:
                current_node_id = current_node_id+1
                new_directive = DirectiveFactory.create(current_location, current_virtualhost, current_if_level, current_context, current_node_id, match_generic_rule.group('name'), current_if_conditions, match_generic_rule.group('args'), current_location_kind)
                directives.append(new_directive)
    return directives