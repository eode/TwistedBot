# -*- coding: utf-8 -*-
# section description for 'help' command.
"""..just an example plugin"""

from twistedbot.behaviours import BehaviourBase
from twistedbot import logbot

log = logbot.getlogger("Example Plugin")


def example(speaker, verb, data,  interface):
    """Just logs a message when you say 'example' in chat."""
    world, factory = interface.world, interface.factory
    full_data = verb + ' ' + data
    log.msg('Example works! Received "%s" from %s ' % (full_data, speaker))


class PluginBehaviour(BehaviourBase):
    pass

verbs = {"example": example}