import math
import time
import re
from const_recovery import recover_used_constants
from context import *
from db_interface import Neo4jDB
from prototype import Directive, DirectiveFactory
from dotenv import load_dotenv
import os

load_dotenv()

def parse_compiled_config(file_path):
    directives = []

    # Regular expressions for extracting relevant information
    # server_name_pattern = re.compile(r'[ \t]*SetEnv (\S+)')
    modsecrule_pattern = re.compile(r'\s*SecRule\s+(.*)')
    generic_rule_pattern = re.compile(r'\s*(?P<name>\w+)\s+(?P<args>.*)')
    virtual_host_pattern = re.compile(r'<VirtualHost\s+(.*?)>')
    virtual_host_end_pattern = re.compile(r'</VirtualHost>')
    location_pattern = re.compile(r'[ \t]*<Location\s+(.*?)>') #gérer locationMatch & directory
    location_end_pattern = re.compile(r'[ \t]*</Location>')
    if_pattern = re.compile(r'[ \t]*<If\s+(.*?)>')
    if_pattern_end = re.compile(r'[ \t]*</If>')
    file_flag = re.compile(r'# In file:\s+(.*)')
    context_regex = re.compile(r'(?:macro \'(.*?)\' \(defined on line (\d+) of "(.*?)"\) used on line (\d+) of "(?P<recursion>.*)")|(?:"?(?P<file_path>\/.*)"?)')
    instruction_number_pattern = re.compile(r'\s*#\s+(\d+):')

    with open(file_path, 'r') as file:
        lines = file.readlines()

    current_virtualhost = ""
    current_location = ""
    current_if_level = 0
    current_ordering_number = 0
    current_context = None
    current_if_conditions = []

    for line in lines:

        # Extract VirtualHost
        match_virtual_host = virtual_host_pattern.match(line)
        if match_virtual_host:
            current_virtualhost = match_virtual_host.group(1)
            current_location = ""
            current_if_level = 0
            continue

        # End VirtualHost
        match_virtual_host_end = virtual_host_end_pattern.match(line)
        if match_virtual_host_end:
            current_virtualhost = ""#match_virtual_host.group(1)
            continue

        # Extract Location
        match_location = location_pattern.match(line)
        if match_location:
            current_location = match_location.group(1)
            continue

        # End Location
        match_location_end = location_end_pattern.match(line)
        if match_location_end:
            current_location = ""

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
                    file_ctx = FileContext(None, infos.group('file_path'))
                    tmp_context.append(file_ctx)
                    break
                else:
                    defined_in = FileContext(int(infos.groups()[1]), infos.groups()[2])
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
            current_ordering_number = current_ordering_number+1
            new_directive = DirectiveFactory.create(current_location, current_virtualhost, current_if_level, current_context, current_ordering_number,"SecRule", current_if_conditions, match_modsecrule.group(1))
            # print(new_directive)
            directives.append(new_directive)
        else:
            match_generic_rule = generic_rule_pattern.match(line)
            if match_generic_rule:
                current_ordering_number = current_ordering_number+1
                new_directive = DirectiveFactory.create(current_location, current_virtualhost, current_if_level, current_context, current_ordering_number, match_generic_rule.group('name'), current_if_conditions, match_generic_rule.group('args'))
                directives.append(new_directive)
        # match_server_name = server_name_pattern.match(line)
        # if match_server_name:
        #     server_name = server_name_pattern.findall(line)[0]
        #     current_ordering_number = current_ordering_number+1
        #     # print(current_macro_stack)
        #     # print(current_instruction_number)
        #     new_directive = Directive(current_location, current_virtualhost, current_if_level, current_context, current_ordering_number,server_name, current_if_conditions)
        #     directives.append(new_directive)

    # print(directives)
    return directives

def estimate_time_left(progress, starting_time, current_time):
    time_taken = current_time - starting_time
    time_left = (time_taken / progress) - time_taken
    return f"{time_left//60:02.0f}m{time_left%60:02.0f}s"

starting_time = time.time()
file_path = "dump.txt"
dbUrl = os.getenv("NEO4J_URL")
dbUser = os.getenv("NEO4J_USER")
dbPass = os.getenv("NEO4J_PASSWORD")
directives = parse_compiled_config(file_path)
print(f"Parsing complete. {len(directives)} directives found.")
db = Neo4jDB(dbUrl, dbUser, dbPass)
step = len(directives) // 100
step = 1 if step == 0 else step
db.query("MATCH (n) DETACH DELETE n")

loop_starting_time = time.time()
for i, directive in enumerate(directives):
    consts = recover_used_constants(directive)
    directive.add_constant(consts)
    db.add(directive)
    if (i+1) % step == 0:
        current_time = time.time()
        elapsed = current_time - loop_starting_time
        print(f"\rProgression: {math.ceil(100*(i+1)/len(directives))}% done. Time elapsed: {f"{elapsed//60:.0f}m" if elapsed >= 60 else ""}{elapsed%60:02.0f}s Time left: {estimate_time_left((i+1)/len(directives), loop_starting_time, current_time)}", end="")

print()
db.close()
end_time = time.time()
time_taken = end_time-starting_time 
print(f"Total time taken: {f"{time_taken//60:.0f}m" if time_taken >= 60 else ""}{f"{time_taken%60:.0f}s" if time_taken%60 > 3 else f"{time_taken}s"}")




# =============================
# sorted_directives = directives #sorted(directives)
# with open("output.txt", "w") as file:
#     for directive in sorted_directives:
#         print(directive, file=file)
# print(f"{len(sorted_directives)} dirs written to output.txt")

# for directive in sorted_directives:
#     print(directive)