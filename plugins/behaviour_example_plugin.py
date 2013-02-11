
from twistedbot.behaviours import BehaviourBase
from twistedbot import logbot

log = logbot.getlogger("Example Plugin")


def example(subject, context):
    """Just logs a message when you say 'example' in chat."""
    word, factory = context['world'], context['factory']
    log.msg('Example works! Received: ' + subject)


class PluginBehaviour(BehaviourBase):
    pass

verbs = {"example": example}