
from src.parser import modsec
from src.parser.const_recovery import recover_used_constants
from src.parser.helper_classes.directives import *


class DirectiveFactory:

    @classmethod
    def create(cls, location, virtual_host, if_level, context, node_id, type, conditions, args):
        if type.lower() == 'secruleremovebytag':
            directive = SecRuleRemoveByTag(location, virtual_host, if_level, context, node_id, type, conditions, args)
        elif type.lower() == 'secruleremovebyid':
            directive = SecRuleRemoveById(location, virtual_host, if_level, context, node_id, type, conditions, args)
        elif type.lower() in ["definestr", "setenv"]:
            directive = DefineStr(location, virtual_host, if_level, context, node_id, type, conditions, args)
        elif type.lower() in ["secrule"]:
            directive = SecRule(location, virtual_host, if_level, context, node_id, type, conditions, args)
        else:
            directive = Directive(location, virtual_host, if_level, context, node_id, type, conditions, args)

        names = recover_used_constants(directive)
        consts, variables = [], []
        for collection, const in names:
            # parsed = const.split(".")
            if collection in modsec.COLLECTIONS:
                variables.extend((collection, const))
            elif collection != "":
                consts.append(collection+"."+const)#TODO change the consts to be a dict with the collection and const
            else:
                consts.append(const)

        directive.add_constant(consts)
        directive.add_variable(variables)
        return directive
