
from twistedbot.behaviours import BehaviourBase
from twistedbot import logbot

log = logbot.getlogger("Example Plugin")


def example(subject, context):
    log.msg('Example works! Received: ' + subject)


class PluginBehaviour(BehaviourBase):
    pass

verbs = {"example": example}