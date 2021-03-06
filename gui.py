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
import signal
import multiprocessing
from time import sleep
from collections import deque

from PyQt4 import QtGui
from PyQt4 import QtCore

import bot
from twistedbot import logbot
from twistedbot.utils import Message
#from resources.splitimages import make_tiles
log = logbot.getlogger("GUI")

#example edit


class MainWindow(QtGui.QMainWindow):
    def __init__(self, argv):
        QtGui.QMainWindow.__init__(self)

        self.to_bot = multiprocessing.Queue()
        self.to_gui = multiprocessing.Queue()

        # Start the bot
        bot_args = (argv, self.to_bot, self.to_gui)
        self.bot = multiprocessing.Process(target=bot.start, args=bot_args)
        self.bot.start()

        # Initialize protocol handlers
        self._init_protocol()

#        # Prepare minecraft images for gui list
#        self._init_minecraft_images()

        #### Build the GUI
        # set up main window with a vbox and grid
        self.mainWidget = QtGui.QWidget(self)
        self.setCentralWidget(self.mainWidget)
        self.vbox = QtGui.QVBoxLayout()
        self.grid = QtGui.QGridLayout()
        self.mainWidget.setLayout(self.vbox)

        # Add the grid to the top of the vbox -- this will contain all of the
        # basic stats items.
        self.vbox.addLayout(self.grid)

        ### Widgets for Information Display
        # For all the widgets we want to update, we make up a variable like
        # self.name or self.health, etc.  We can display the information with
        # a "QLabel", which is just a text display widget.
        ## Widgets for location
        # This one isn't assigned to 'self', so it'll be harder to access
        # later on.  But we don't need to update it, so that's fine.
        name = QtGui.QLabel("Position:")
        # These ones we want to update later, so we attach them all to self
        # (which is our instance of MainWindow), so we can use them in other
        # methods.
        self.bot_x = QtGui.QLabel('x:')
        self.bot_y = QtGui.QLabel('y:')
        self.bot_z = QtGui.QLabel('z:')
        # Now that we've attached them, we need to put them in the window to
        # display.  The window already has a grid widget in it, so we can use
        # that. grid's "addWidget" methods allow us to set where on the grid
        # these should go.
        # self.grid.addWidget(widget_to_add, row, column), starting at 0.
        # We'll put these on row 0.  Using a variable means we can easily
        # rearrange what user data we see first.
        row = 0
        self.grid.addWidget(name, row, 0)        # same as (name, 0, 0)
        self.grid.addWidget(self.bot_x, row, 1)  # same as (self.bot_x, 0, 1)
        self.grid.addWidget(self.bot_y, row, 2)  # same as (self.bot_y, 0, 2)
        self.grid.addWidget(self.bot_z, row, 3)  # same as (self.bot_z, 0, 3)

        # Widgets for health
        self.health = QtGui.QLabel('Health: ')
        self.food = QtGui.QLabel('Food: ')
        # We'll do these on the second row (row 1).
        row = 1
        self.grid.addWidget(QtGui.QLabel('Stats:  '), row, 0)
        self.grid.addWidget(self.health, row, 1)
        self.grid.addWidget(self.food, row, 2)

        # Items list
        self.items_index = {}
        self.items = QtGui.QTreeWidget()
        self.items.doubleClicked.connect(self.on_item_list_double_click)
        self.items.setHeaderLabels(['Count', 'Item'])
        self.vbox.addWidget(self.items)

        # drop item buttons
        drop_one = QtGui.QPushButton("Drop One")
        drop_stack = QtGui.QPushButton("Drop Stack")
        drop_all = QtGui.QPushButton("Drop All")
        drop_one.clicked.connect(self.on_drop_one_clicked)
        drop_stack.clicked.connect(self.on_drop_stack_clicked)
        drop_all.clicked.connect(self.on_drop_all_clicked)
        self.drop_button_box = QtGui.QHBoxLayout()
        self.drop_button_box.addWidget(drop_one)
        self.drop_button_box.addWidget(drop_stack)
        self.drop_button_box.addWidget(drop_all)
        self.vbox.addLayout(self.drop_button_box)

        # Start the local event loop to update GUI
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.local_event_loop)
        self.timer.start(500)   # milliseconds

#TODO: use images for inventory display
#    def _init_minecraft_images(self):
#        """Load all of the png images from the resources folder."""
#        # This originally would have tiled the full image file, but that
#        # requires PIL, which is a pain to install on OSX, and I didn't want
#        # to add another dependency.
#        #images = make_tiles('resources/items.png', 16, 16)
#        fnames = glob.glob('resources/items/*-*.png')
#        images = {}
#        for name in fnames:
#            xy = name.rsplit('/')[-1].split('.')[0].split('-')
#            x, y = [int(n) for n in xy]
#            images[x, y] = "ToDo"

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
            # The bot is shutting down.
            'shutting down': self._mh_shut_down,
            # ..you can copy and edit this and _mh_template (below)
            'update items': self._mh_update_items,
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
            if message.name == "shutdown ok":
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
                msg = (msg % message.name) + str(message.data)
                log.msg(msg)
                log.err()
        for name in latest_only:
            data = latest_only[name]
            try:
                self.message_handlers[name](data)
            except Exception:
                msg = "Error in message handler %s while handling this data:\n"
                msg = (msg % name) + str(data)
                log.msg(msg)
                log.err()

    def on_item_list_double_click(self, index):
        #log.msg(str(dir(index)))
        this_row = index.row()
        root = self.items.invisibleRootItem()
        item = root.child(this_row)
        log.msg(str(item.minecraft_item))
        self.to_bot.put(Message('gui clicked item', item.minecraft_item))

    def on_drop_one_clicked(self, *args):
        self.to_bot.put(Message('drop one', None))

    def on_drop_stack_clicked(self, *args):
        self.to_bot.put(Message('drop stack', None))

    def on_drop_all_clicked(self, *args):
        self.to_bot.put(Message('drop all', None))

    def _mh_bot_name(self, name):
        """Updates the window title with the bot's name."""
        # this sets the window title to include the bot's name.
        self.setWindowTitle("Minecraft bot: " + name)

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

    def _mh_shut_down(self, data):
        """Shutdown sent by bot.py.  We may want to turn this into something
        that restarts the bot, or that announces to the GUI that the bot has
        shut down."""
        log.msg("Shutting down GUI: " + data)
        self.app.quit()

    def _mh_template(self, data):
        """You should describe what your method does here.
        This can be more than one line."""
        # This is a template you can copy and paste.  Make sure to register
        # this method with the method_handlers variable above, or it will
        # never get called.
        log.msg("Template data (not handled yet):\n" + str(data))

    def _mh_update_items(self, data):
        """The full list of items is sent here from the bot.  The actual
        changing of the GUI is deferred for a half second, as the server will
        often send updates of items in bursts."""
        ## as an initial run, let's just clear the items treeview, and add
        ## all the new ones.
        ## ..and, this works fine, so, perhaps I'll just leave it this way.
        while self.items.topLevelItemCount():
            self.items.takeTopLevelItem(0)
        data.sort(key=lambda x: x.name)
        for item in data:
            qitem = QtGui.QTreeWidgetItem([str(item.count), item.name])
            qitem.minecraft_item = item
            self.items.addTopLevelItem(qitem)

    def close(self, *args, **kwargs):
        print args
        print kwargs
        self.to_bot.put('shutting down')
        QtGui.QMainWindow.close(self, *args, **kwargs)


if __name__ == "__main__":
    counter = list('123')

    def customKeyboardInterruptHandler(signum, stackframe):
        """Ignore ctrl-c from user"""
        counter.pop()
        if counter:
            log.msg("ctrl-c: waiting for bot to exit cleanly")
            return
        log.msg("Third time's a charm..")
        exit(130)
    signal.signal(signal.SIGINT, customKeyboardInterruptHandler)

    app = QtGui.QApplication(sys.argv)
    main = MainWindow(sys.argv)
    main.app = app
    main.show()
    app.exec_()
