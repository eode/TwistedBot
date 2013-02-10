
import signal
import argparse
import socket

import syspath_fix
syspath_fix.update_sys_path()

from twisted.internet import reactor, task
from twisted.protocols import basic

from twistedbot.factory import MineCraftFactory
from twistedbot.world import World
import twistedbot.config as config
import twistedbot.logbot as logbot

log = logbot.getlogger("MAIN")


class ConsoleChat(basic.LineReceiver):
    def __init__(self, world):
        self.world = world

    def lineReceived(self, line):
        try:
            self.world.chat.process_command(line)
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
    try:
        from twisted.internet import stdio
        stdio.StandardIO(ConsoleChat(world))
    except ImportError:
        pass
    mc_factory = MineCraftFactory(world)
    return world, mc_factory


def start(argv, to_bot=None, to_gui=None):
    args = parse_args(argv)
    world, mc_factory = initialize_bot(args, to_bot, to_gui)

    def customKeyboardInterruptHandler(signum, stackframe):
        """Handle ctrl-c"""
        reactor.callFromThread(mc_factory.shut_down, "CTRL-C from user")
    signal.signal(signal.SIGINT, customKeyboardInterruptHandler)

    def gui_integration_loop():
        """Communicate with GUI, if there is one"""
        if not to_bot.empty():
            message = to_bot.get()
            if message.name == "shut down":
                world.to_gui("shutdown ok", '')
                message = "'shut down' received from GUI"
                reactor.callFromThread(mc_factory.shut_down, message)
    if to_bot and to_gui:
        gui_loop = task.LoopingCall(gui_integration_loop)
        gui_loop.start(0.25)
        reactor.addSystemEventTrigger("before", "shutdown", gui_loop.stop)

    # run the bot
    reactor.connectTCP(args.serverhost, args.serverport, mc_factory)
    reactor.run()


if __name__ == '__main__':
    import sys
    start(sys.argv)
