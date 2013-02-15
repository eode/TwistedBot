
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
        self.command_str = config.COMMAND_SHORTCUT
        self.wspace_re = re.compile(ur"\s+")
        self.chat_spam_threshold_count = 0
        self.chat_spam_threshold_buffer = deque()
        self.message_cost = 20 * 1    # one message per second
        self.free_messages = 20 * 3   # Three free messages before regulating
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
        if self.chat_spam_threshold_count > 0:
            self.chat_spam_threshold_count -= 1
        if self.chat_spam_threshold_count <= self.free_messages \
          and self.chat_spam_threshold_buffer:
            message, who = self.chat_spam_threshold_buffer.popleft()
            self._send_chat_message(message, who)

    def send_chat_message(self, msg, who=config.COMMANDER):
        self.chat_spam_threshold_buffer.append((msg, who))

    def _send_chat_message(self, msg, who):
        self.chat_spam_threshold_count += self.message_cost
        prefix = ''
        if config.WHISPER:
            prefix = '/tell ' + who
            msg = prefix + msg
        if len(msg) >= 100:
            # Minecraft server balks at messages greater than 100 characters.
            # split them up and push them into the spam buffer.
            # cut this message in half and put it at the beginning
            plen = len(prefix)
            msg = msg[plen:]  # remove from current message
            # shove the pieces back up the queue so they're next
            beginning, end = msg[:100 - plen - 1], msg[100 - plen - 1:]
            for message in (end, beginning):
                self.chat_spam_threshold_buffer.appendleft((message, who))
            return
        log.msg(">> %s" % msg)
        self.world.send_packet("chat message", {"message": msg})

    def on_chat_message(self, msg):
        """Split the chat message into speaker and message, and accept it if
        it's from an authority (commander or managers)"""
        log.msg("<< %s" % msg)
        speaker, message = msg.split(None, 1)
        speaker = speaker.strip('<>')
        self.process_command(speaker, self.clean(message))

    def clean(self, orig_msg):
        msg = self.clean_colors_re.sub('', orig_msg)
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
        context = {'chat': self, 'world': self.world,
                   'factory': self.world.factory}
        if verb in self.verbs:
            self.verbs[verb](speaker, verb, data, context)
        else:
            self.send_chat_message("Unknown command: %s %s " % (verb, data))

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
        first, message = fm if len(fm) == 2 else fm[0], ''
        if first.strip(ignored).lower() == config.USERNAME.lower():
            return message
        return ''