
import re
from collections import deque

import config
import behaviours
import logbot
import plugins

log = logbot.getlogger("CHAT")


class Chat(object):
    def __init__(self, world):
        self.world = world
        self.clean_colors_re = re.compile(ur'\u00A7.', re.UNICODE)
        self.commander_re = re.compile(
            ur'<%s> .*' % self.world.commander.name.lower(), re.UNICODE)
        self.wspace_re = re.compile(ur"\s+")
        self.chat_spam_treshold_count = 0
        self.chat_spam_treshold_buffer = deque()
        self.verbs = {}
        for plugin in plugins.behaviours:
            plugin = plugins.behaviours[plugin]
            for verb in plugin.verbs:
                if verb in self.verbs:
                    log.msg('Cannot override pre-existing verb "%s"' % verb)
                    continue
                else:
                    self.verbs[verb] = plugin.verbs[verb]

    def tick(self):
        if self.chat_spam_treshold_count > 0:
            self.chat_spam_treshold_count -= 1
        if self.chat_spam_treshold_count <= 160 and self.chat_spam_treshold_buffer:
            self.send_chat_message(self.chat_spam_treshold_buffer.popleft())

    def send_chat_message(self, msg):
        log.msg(">> %s" % msg)
        if self.world.commander.in_game:
            self.chat_spam_treshold_count += 20
            if self.chat_spam_treshold_count > 180:
                self.chat_spam_treshold_buffer.append(msg)
                return
            if config.WHISPER:
                msg = "/tell %s %s" % (self.world.commander.name, msg)
            self.world.send_packet("chat message", {"message": msg})
        elif self.chat_spam_treshold_buffer:
            self.chat_spam_treshold_buffer = deque()

    def clean(self, orig_msg):
        msg = self.clean_colors_re.sub('', orig_msg)
        msg = self.wspace_re.sub(" ", msg)
        msg = msg.strip().lower()
        return msg

    def from_commander(self, msg):
        return self.commander_re.match(msg)

    def get_command(self, msg):
        return msg[msg.find(">") + 2:]

    def get_verb(self, msg):
        return msg.partition(" ")[0]

    def get_subject(self, msg):
        return msg.partition(" ")[2]

    def on_chat_message(self, msg):
        msg = self.clean(msg)
        log.msg("<< %s" % msg)
        if self.from_commander(msg):
            command = self.get_command(msg)
            self.process_command(command, msg)

    def process_command(self, command, msg=None):
        if msg is None:
            msg = command
        log.msg("Possible command >%s<" % command)
        verb = self.get_verb(command)
        subject = self.get_subject(command)
        self.parse_command(verb, subject, msg)

    def parse_command(self, verb, subject, original):
        if verb in self.verbs:
            context = {'chat': self, 'world': self.world,
                       'factory': self.world.factory}
            self.verbs[verb](subject, context)
        else:
            context['chat'].send_chat_message("Unknown command: %s"
                                              % verb + subject)
