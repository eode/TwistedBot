# -*- coding: utf-8 -*-

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
#        self.clean_colors_re = re.compile(ur'\xA7.', re.UNICODE)
        self.command_str = config.COMMAND_SHORTCUT
        self.wspace_re = re.compile(ur"\s+")
        self.spam_threshold_count = 0
        self.message_buffer = deque()
        self.message_cost = 20 * 1    # one message per second
        self.free_messages = 20 * 3   # Three free messages before regulating
        # Max length (in characters, not bytes) allowed for a message
        self.size_max = 100

    @property
    def verbs(self):
        return self.world.bot.controller.verbs

    def tick(self):
        if not self.world.connected:
            return
        if self.spam_threshold_count > 0:
            self.spam_threshold_count -= 1
        if self.spam_threshold_count <= self.free_messages \
          and self.message_buffer:
            message, who, whisper = self.message_buffer.popleft()
            self._send_message(message, who, whisper)

    def send_message(self, msg, who=None, whisper=config.WHISPER):
        if who is None:
            who = self.world.commander.name
        msg = msg.strip().replace('\t', '    ')  # tab is an illegal character
        if '\n' in msg:
            for part in msg.split('\n'):
                self.message_buffer.append((part, who, whisper))
            return
        else:
            self.message_buffer.append((msg, who, whisper))
        self.tick()  # Run a tick now, to keep log messages in order

    def _send_message(self, msg, who, whisper):
        self.spam_threshold_count += self.message_cost
        prefix = ''
        if whisper:
            prefix = '/tell %s ' % who
        # Somehow, a message is two extra characters longer.  In theory, the
        # full packet should be at most 203 bytes --
        # packet id (1), unicode prefix (2), len(string) * 2
        # ..but, there's an extra two chars / four bytes that get lopped off
        # by the server or locally for some reason..  oh well.
        plen = len(prefix) + 2   # 2 fewer characters than the max
        if len(msg) + plen > self.size_max:
            split = self.size_max - plen
            # look up to 15 chars before required split for a space to break on
            found_space = msg.rfind(' ', split - 15, split)
            if found_space != -1:
                split = found_space + 1
            unsent = msg[split:]
            msg = msg[:split]
            # shove the second piece back on the queue so it's next
            self.message_buffer.appendleft((unsent, who, whisper))
        msg = prefix + msg
        log.msg(">> %s" % msg)
        self.world.send_packet("chat message", {"message": msg})

    def on_chat_message(self, msg):
        """Split the chat message into speaker and message, and accept it if
        it's from an authority (commander or managers)"""
        msg = self.clean(msg)
        log.msg("<< %s" % msg)
        speaker, message = msg.split(None, 1)
        speaker = speaker.strip('<>')
        self.process_command(speaker, message)

    def clean(self, msg):
        """Minecraft messages may contain a control character '\xa7' which is
        then followed by one of '0123456789abcdefklmnor'.  Not to mention not
        being useful, these interfere with twisted's logging.  ..so, we strip
        them.  In theory, if a player could send a message with the 'random'
        style, twistedbot would still be able to read the message (while others
        would not, unless they had a client that strips the 'random' flag and
        control character).
        """
        control_char = u'\xa7'
        while control_char in msg:
            loc = msg.find(control_char)
            msg = msg[:loc] + msg[loc + 2:]
        msg = self.wspace_re.sub(" ", msg)
        msg = msg.strip()
        return msg

    def process_command(self, speaker, message):
        """Determine if the message makes sense.  Accept it if it does, and
        reject it if it doesn't."""
        if not self._is_authoritative(speaker):
            return
        command = self._get_command(message)
        if not command:
            return
        log.msg("Message addressed to me: >%s<" % command)
        verbdata = command.split(None, 1)
        verb, data = verbdata if len(verbdata) == 2 else (verbdata[0], '')
        # Now, we'll execute the appropriate plugin.
        if verb in self.verbs:
            self.verbs[verb](speaker, verb, data, self.world.bot.controller)
        else:
            self.send_message("Unknown command: %s %s " % (verb, data))

    def _is_authoritative(self, speaker):
        if speaker.lower() == config.COMMANDER.lower()\
          or speaker in self.world.managers:
            return True

    def _get_command(self, message):
        """Returns the full command minus the command character/bot name if
        the message is addressed to the bot, otherwise, returns an empty
        string."""
        # It is a valid command if it starts with the command shortcut
        if message.startswith(self.command_str):
            message = message[len(self.command_str):]
            return message
        # ..or with the bot's name (possibly ending with one of ,.!?:;)
        ignored = ',.!?:;'  # Ignore these if they're pended to bot name
        fm = message.split(None, 1)
        first, message = fm if len(fm) == 2 else (fm[0], '')
        if first.strip(ignored).lower() == config.USERNAME.lower():
            return message
        return ''