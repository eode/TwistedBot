# -*- coding: utf-8 -*-

from twistedbot.behaviours import BehaviourBase
from twistedbot import logbot

log = logbot.getlogger("Example Plugin")


def example(speaker, verb, data,  context):
    """Just logs a message when you say 'example' in chat."""
    world, factory = context['world'], context['factory']
    log.msg('Example works! Received: ' + subject)


class PluginBehaviour(BehaviourBase):
    pass

verbs = {"example": example}