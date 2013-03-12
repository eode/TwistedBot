#! python
# -*- coding: utf-8 -*-
"""
A bot for minecraft

This bot has an accompanying gui, but can be run with or without the gui.

To execute the bot alone, use:
    python bot.py
To execute the bot and gui, use:
    python gui.py
"""

import signal
import argparse
import socket
import os

import syspath_fix
syspath_fix.update_sys_path()

from twisted.internet import reactor, task
from twisted.protocols import basic

from twistedbot.factory import MineCraftFactory
from twistedbot.world import World
import twistedbot.config as config
import twistedbot.logbot as logbot

log = logbot.getlogger("MAIN")


##TODO: having this working might be handy..
class ConsoleChat(basic.LineReceiver):
    delimiter = os.linesep

    def __init__(self, world):
        self.world = world

    def lineReceived(self, line):
        if not line.strip():
            return
        try:
            line = ("<%s> !" % config.COMMANDER) + line.lstrip()
            self.world.chat.on_chat_message(line)
        except Exception as e:
            logbot.exit_on_error(e)


def parse_args(argv):
    # defaults me as commander when on my system. :-)
    host = socket.gethostname()
    commander = 'eode' if host == 'foxglove' else config.COMMANDER

    parser = argparse.ArgumentParser(description='Bot arguments.',
                                     prog=argv[0])
    parser.add_argument('--serverhost', default=config.SERVER_HOST,
                        dest='serverhost', help='Minecraft server host')
    parser.add_argument('--serverport', type=int, default=config.SERVER_PORT,
                        dest='serverport', help='Minecraft server port')
    parser.add_argument('--botname', default=config.USERNAME,
                        dest='botname',
                        help='username that will be used by the bot')
    parser.add_argument('--commandername', default=commander,
                        dest='commandername',
                        help='your username that you use in Minecraft')
    parser.add_argument('--log2file',
                        action='store_true',
                        help='Save log data to file')
    return parser.parse_args(args=argv[1:])


def initialize_bot(args, to_bot=None, to_gui=None):
    if args.log2file:
        logbot.start_bot_filelog()
    config.USERNAME = args.botname
    config.COMMANDER = args.commandername
    world = World(host=args.serverhost, port=args.serverport,
                  commander_name=args.commandername, bot_name=args.botname,
                  to_bot_q=to_bot, to_gui_q=to_gui)
    reactor.addSystemEventTrigger("before", "shutdown", world.on_shutdown)
    mc_factory = MineCraftFactory(world)
    world.reactor = reactor
    return world, mc_factory


class GuiProtocol(object):
    """Just a container object for protocol methods coming from gui"""
    def __init__(self, reactor, mc_factory, world):
        self.reactor = reactor
        self.mc_factory = mc_factory
        self.world = world
        self.methods = {
            'drop all': self.on_gui_clicked_drop_all,
            'drop one': self.on_gui_clicked_drop_one,
            'drop stack': self.on_gui_clicked_drop_stack,
            'gui clicked item': self.on_gui_clicked_item,
            "shut down": self.on_shut_down,
            }

    def gui_integration_loop(self):
        """Communicate with GUI, if it is loaded"""
        message = self.world.to_bot()
        if message is None:
            return
        if message.name in self.methods:
            self.methods[message.name](message.data)
        else:
            log.msg("Unhandled Protocol Item from GUI: " + str(message))

    def on_gui_clicked_drop_all(self, data):
        self.world.bot.interface.drop_everything()

    def on_gui_clicked_drop_one(self, data):
        self.world.bot.interface.drop(1)

    def on_gui_clicked_drop_stack(self, data):
        self.world.bot.interface.drop(-1)

    def on_gui_clicked_item(self, data):
        received_item = data
        inventory = self.world.bot.interface.inventory
        item = inventory[received_item.window_slot_number]
        if item.name != received_item.name:
            return
        self.world.bot.interface.hold(item, lookup=False)

    def on_shut_down(self, data):
        self.world.to_gui("shutdown ok", '')
        message = "'shut down' received from GUI"
        self.reactor.callFromThread(self.mc_factory.shut_down, message)


def start(argv, to_bot=None, to_gui=None):
    args = parse_args(argv)
    world, mc_factory = initialize_bot(args, to_bot, to_gui)

    def customKeyboardInterruptHandler(signum, stackframe):
        """Handle ctrl-c"""
        reactor.callFromThread(mc_factory.shut_down, "CTRL-C from user")
    signal.signal(signal.SIGINT, customKeyboardInterruptHandler)

    if to_bot and to_gui:
        gui_protocol = GuiProtocol(reactor, mc_factory, world)
        gui_loop = task.LoopingCall(gui_protocol.gui_integration_loop)
        gui_loop.start(0.25)
        reactor.addSystemEventTrigger("before", "shutdown", gui_loop.stop)

    # console input
    try:
        from twisted.internet import stdio
        stdio.StandardIO(ConsoleChat(world))
    except ImportError:
        pass
    # run the bot
    reactor.connectTCP(args.serverhost, args.serverport, mc_factory)
    reactor.run()


if __name__ == '__main__':
    import sys
    start(sys.argv)
