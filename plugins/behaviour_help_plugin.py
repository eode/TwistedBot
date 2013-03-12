# -*- coding: utf-8 -*-
# section description for 'help' command.
"""the help system"""
from twistedbot import logbot

log = logbot.getlogger("HELP PLUGIN")

def help(speaker, verb, data,  interface):
    """"help" or "help <section>" or "help <command>" or "help <section/command>" """
    data = data.strip()
    if not data:
        help_msg = ["""Sections are:"""]
        for section in interface.behaviours:
            mod = interface.behaviours[section]
            help_msg.append(section + " - " + mod.__doc__ if mod.__doc__
                            else section)
        help_msg.append('Use "help <section>" for more info.')
        help_msg = '\n'.join(help_msg)
    elif '/' in data:
        section, command = [d.strip() for d in data.split('/'), 1]
        if section not in interface.behaviours:
            msg = "Unknown section for help: '%s'" % section
            interface.world.chat.send_message(msg)
            log.msg(msg)
            return
        verbs = interface.behaviours[section].verbs
        if command not in verbs:
            msg = "Unknown command for section %s: %s" % (section, command)
            interface.world.chat.send_message(msg)
            log.msg(msg)
            return
        func = verbs[command]
        if func.__doc__ is None:
            help_msg = "%s/%s - No help available" % (section, command)
        else:
            help_msg = func.__doc__
    elif data in interface.behaviours:
        module = interface.behaviours[data]
        help_msg = "Verbs are: "
        help_msg = help_msg + ', '.join(v for v in module.verbs)
        help_msg = help_msg + '\nUse "help <verb>" for more info.'
    elif data in interface.verbs:
        help_msg = interface.verbs[data].__doc__
        help_msg = help_msg if help_msg else "no help available"
    else:
        help_msg = "huh?"
    for message in help_msg.split('\n'):
        interface.world.chat.send_message(message)


verbs = {"help": help}