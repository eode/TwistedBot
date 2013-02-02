# -*- coding: utf-8 -*-
"""
Created on Fri Feb  1 08:57:21 2013

@author: Brian Visel <eode@eptitude.net>
"""

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from Queue import Empty
from collections import deque
import multiprocessing
import sys

import bot
from twistedbot import logbot

log = logbot.getlogger("GUI")

class MainWindow(QMainWindow):
    def __init__(self, argv):
        QMainWindow.__init__(self)

        self.to_bot = multiprocessing.Queue()
        self.to_gui = multiprocessing.Queue()

        # Start the bot
        bot_args = (argv, self.to_bot, self.to_gui)
        self.bot = multiprocessing.Process(target=bot.start, args=bot_args)
        self.bot.start()

        # Initialize protocol handlers
        self._init_protocol()

        # Build the GUI
        self.mainWidget = QWidget(self)
        self.setCentralWidget(self.mainWidget)
        self.grid = QGridLayout()
        self.mainWidget.setLayout(self.grid)
        # Widgets for location
        name = QLabel("Position:")
        self.bot_x = QLabel('x:')
        self.bot_y = QLabel('y:')
        self.bot_z = QLabel('z:')
        row1 = [name, self.bot_x, self.bot_y, self.bot_z]
        for i in xrange(len(row1)):
            self.grid.addWidget(row1[i], 0, i)
        # Widgets for health
        self.health = QLabel('')
        self.grid.addWidget(self.health, 1, 0)

        # Start the local event loop to update GUI
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.local_event_loop)
        self.timer.start(500)   # milliseconds

    def _init_protocol(self):
        self.messages = deque()
        # Message handler registry
        self.message_handlers = {
            'location': self._p_location,
            'bot name': self._p_bot_name,
            'health update': self._p_health_update,
            }

    def local_event_loop(self, milliseconds=None):
        """This code is executed every ~.5 seconds (or whatever is configured
        in __init__)"""
        while not self.to_gui.empty():
            value = self.to_gui.get()
            try:
                name, data = value
            except ValueError:
                msg = "Tried to unpack malformed message from bot:\n"
                log.error(msg + str(value))
            self.messages.append(value)
        while self.messages:
            key, value = self.messages.popleft()
            try:
                self.message_handlers[key](value)
            except Exception:
                msg = "Error in message handler %s while handling this data:\n"
                msg = (msg % key) + str(value)
                log.error(msg, exc_info=True)

    def _p_bot_name(self, name):
        self.setWindowTitle("Minecraft bot: " + name[0])

    def _p_health_update(self, data):
        self.health.setText(str(data))

    def _p_location(self, c):
        self.bot_x.setText("x:" + str(c.position.x))
        self.bot_y.setText("y:" + str(c.position.y))
        self.bot_z.setText("z:" + str(c.position.z))

    def close(self, *args, **kwargs):
        print args
        print kwargs
        self.to_bot.put('shutting down')
        QMainWindow.close(self, *args, **kwargs)


if __name__ == "__main__":
    defaults = sys.argv + ['--commandername', 'eode',
                           '--botname', 'Bottington']
    argv = defaults if len(sys.argv) is 1 else sys.argv
    app = QApplication(argv)
    main = MainWindow(argv)
    main.show()
    app.exec_()


