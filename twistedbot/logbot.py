
import sys
import os
from datetime import datetime
import traceback

from twisted.internet import reactor
from twisted.python import log, util


def exit_on_error(_stuff=None, _why=None):
    log.err(_stuff=_stuff, _why=_why)
    try:
        reactor.stop()
    except:
        pass


class MinecraftLogObserver(object):

    def __init__(self, f):
        self.write = f.write
        self.flush = f.flush

    def formatTime(self, when):
        t = datetime.fromtimestamp(when)
        return t.strftime("%H:%M:%S.%f")

    def emit(self, eventDict):
        if "isError" in eventDict and \
                eventDict["isError"] and \
                "header" not in eventDict:
            eventDict["header"] = "-"
        if "header" not in eventDict:
            return
        text = log.textFromEventDict(eventDict)
        if text is None:
            return
        timeStr = self.formatTime(eventDict['time'])
        fmtDict = {'header': eventDict['header'], 'text':
                   text.replace("\n", "\n\t")}
        msgStr = log._safeFormat("[%(header)s] %(text)s\n", fmtDict)
        msgStr = timeStr + " " + msgStr

        util.untilConcludes(self.write, msgStr.encode(sys.stdout.encoding))
        util.untilConcludes(self.flush)


class Logger(object):

    def __init__(self, name):
        self.name = name

    def msg(self, *args, **kwargs):
        # log traceback if requested.
        args = list(args)
        if 'exc_info' in kwargs:
            if kwargs.pop('exc_info'):
                args.append('\n' + traceback.format_exc())
        if "header" not in kwargs:
            kwargs["header"] = self.name
        log.msg(*args, **kwargs)

    def err(self, *args, **kwargs):
        if "header" not in kwargs:
            kwargs["header"] = self.name
        log.err(*args, **kwargs)


loggers = {}


def getlogger(name):
    if name not in loggers:
        loggers[name] = Logger(name)
    return loggers[name]


def start_filelog(filename=None, kind="other_log"):
    if filename is None:
        timefmt = "%Y.%m.%d_%H.%M.%S"
        filename = "%s.%s.txt" % (kind, datetime.now().strftime(timefmt))
    fullfile = os.getcwd() + filename
    try:
        f = open(filename, "w")
    except IOError as e:
        msg("Cannot open log file %s for writing" % fullfile)
        msg("%s" % e)
        msg("Exiting...")
        sys.exit()
    log.addObserver(MinecraftLogObserver(f).emit)
    msg("Started logging to file %s" % fullfile)


def start_bot_filelog():
    start_filelog(kind="bot_log")


def start_proxy_filelog():
    start_filelog(kind="proxy_log")


log.startLoggingWithObserver(MinecraftLogObserver(sys.stdout).emit,
                             setStdout=0)
default_logger = getlogger("-")
default_logger.msg("Start logging")
msg = default_logger.msg
err = default_logger.err
