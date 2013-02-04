# -*- coding: utf-8 -*-
"""
Created on Fri Feb  1 08:57:21 2013

@author: Brian Visel <eode@eptitude.net>

This is a basic UI for displaying data about the bot (or that the bot can
access).

1) Create Widgets in the UI, and fill them with blank defaults
2) Send your information from the bot as a Message via world.to_gui.put
   (look in factory.py for some examples - search for 'to_gui')
3) Add the Message name (and a new method name) to MainWindow.message_handlers
4) Write a method using the new method name that updates the gui widgets

There are comments in each area to help you.
"""

import sys
import multiprocessing
from collections import deque, namedtuple
from time import sleep
from PyQt4.QtGui import *
from PyQt4.QtCore import *
#from Queue import Empty

import bot
from twistedbot import logbot
from twistedbot.utils import Message

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

        #### Build the GUI
        self.mainWidget = QWidget(self)
        self.setCentralWidget(self.mainWidget)
        self.grid = QGridLayout()
        self.mainWidget.setLayout(self.grid)

        ### Widgets for Information Display
        # For all the widgets we want to update, we make up a variable like
        # self.name or self.health, etc.  We can display the information with
        # a "QLabel", which is just a text display widget.
        ## Widgets for location
        # This one isn't assigned to 'self', so it'll be harder to access
        # later on.  But we don't need to update it, so that's fine.
        name = QLabel("Position:")
        # These ones we want to update later, so we attach them all to self
        # (which is our instance of MainWindow), so we can use them in other
        # methods.
        self.bot_x = QLabel('x:')
        self.bot_y = QLabel('y:')
        self.bot_z = QLabel('z:')
        # Now that we've attached them, we need to put them in the window to
        # display.  The window already has a grid widget in it, so we can use
        # that. grid's "addWidget" methods allow us to set where on the grid
        # these should go.
        # self.grid.addWidget(widget_to_add, row, column), starting at 0.
        # We'll put these on row 0.  Using a variable means we can easily
        # rearrange what user data we see first.
        row = 0
        self.grid.addWidget(name, row, 0) # same as (name, 0, 0)
        self.grid.addWidget(self.bot_x, row, 1)  # same as (name, 0, 1)
        self.grid.addWidget(self.bot_y, row, 2)  # same as (name, 0, 2)
        self.grid.addWidget(self.bot_z, row, 3)  # same as (name, 0, 3)

        # Widgets for health
        self.health = QLabel('Health: ')
        self.food = QLabel('Food: ')
        # We'll do these on the second row (row 1).
        row = 1
        self.grid.addWidget(QLabel('Stats:  '), row, 0)
        self.grid.addWidget(self.health, row, 1)
        self.grid.addWidget(self.food, row, 2)

        # Start the local event loop to update GUI
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.local_event_loop)
        self.timer.start(500)   # milliseconds

    def _init_protocol(self):
        """Set up everything having to do with protocol between bot and GUI"""
        self.messages = deque()
        ## Message handler registry
        # here is where you register a method to handle data from the bot.
        # The local_event_loop method will receive a Message, and look in here
        # to see if its name is in here.  If it is, it uses the method
        # associated here, and sends it the message's data.
        # So that it's easy to find, name your message_handlers starting with
        # "_mh_", and try to keep them similar to the Message name.
        self.message_handlers = {
            # Messages named "health update" are sent to _mh_health_update.
            'health': self._mh_health_update,
            # Messages with the name "location" are sent to _mh_location.
            'location': self._mh_location,
            # ..same idea here.
            'name': self._mh_bot_name,
            # ..you can copy and edit this and _mh_template (below)
            'template': self._mh_template,
            }
            # You can see where _mh_bot_name and others are defined below.

        # Make sure you add your message name here if your method only needs
        # the latest data.  This saves a lot of useless processing.
        self.latest_only = set(['health update', 'location', 'bot name',
                               'template'])

    def closeEvent(self, event):
        self.to_bot.put(Message('shut down', 'User closed GUI window'))
        while True:
            message = self.to_gui.get()
            if not isinstance(message, Message):
                log.msg("Bad Message during shutdown: %s" % str(message))
            if message.name == "shutdown complete":
                break
            sleep(0.05)
        event.accept()


    def local_event_loop(self, milliseconds=None):
        """This code is executed every ~.5 seconds (or whatever is configured
        in __init__).  It handles receiving messages from the bot."""
        # read all of the messages
        while not self.to_gui.empty():
            message = self.to_gui.get()
            if not isinstance(message, Message):
                #message is not a Message.  ..try to convert it.
                try:
                    # use message parameters to Message, converting it to a..
                    # ..you guessed it. Message.
                    message = Message(*message)
                except:
                    log.msg("Bad Message: " + str(message))
                continue
            self.messages.append(message)
        #Route all of the messages to their respective methods.
        latest_only = {}
        while self.messages:
            message = self.messages.popleft()
            try:
                # if the message only needs the latest packet
                if message.name in self.latest_only:
                    # add it to the local dict of latest-only packets.
                    # latest packet for each name will be the last one set.
                    latest_only[message.name] = message.data
                    continue
                # otherwise, handle the packet.
                self.message_handlers[message.name](message.data)
            except Exception:
                msg = "Error in message handler %s while handling this data:\n"
                msg = (msg % key) + str(value)
                log.error(msg, exc_info=True)
        for name in latest_only:
            data = latest_only[name]
            try:
                self.message_handlers[name](data)
            except Exception:
                msg = "Error in message handler %s while handling this data:\n"
                msg = (msg % key) + str(value)
                log.error(msg, exc_info=True)


    def _mh_bot_name(self, name):
        """Updates the window title with the bot's name."""
        # this sets the window title to include the bot's name.
        self.setWindowTitle("Minecraft bot: " + data[0])

    def _mh_health_update(self, data):
        """Updates the health info in the GUI"""
        # food: data.fp, health: data.hp, saturation: data.saturation
        # Saturation is an additional food value that increases with any food
        # eaten, but cannot go above the current fp.
        health = (data.hp / 20.0) * 100
        food = ((data.fp + data.saturation) / 20.0) * 100
        self.health.setText("Health: %i%%" % health)
        self.food.setText("Food: %i%%" % food)

    def _mh_location(self, data):
        """Updates the location info in the GUI"""
        # Location in x, y, and z.  The data includes some other stuff, like
        # where the bot is looking, but we just use the position data here.
        self.bot_x.setText("x:" + str(data.position.x))
        self.bot_y.setText("y:" + str(data.position.y))
        self.bot_z.setText("z:" + str(data.position.z))

    def _mh_template(self, data):
        """You should describe what your method does here.
        This can be more than one line."""
        # This is a template you can copy and paste.  Make sure to register
        # this method with the method_handlers variable above, or it will
        # never get called.
        log.msg("Template data (not handled yet):\n" + str(data))

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


