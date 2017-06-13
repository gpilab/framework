#    Copyright (C) 2014  Dignity Health
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#    NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL PURPOSES
#    AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
#    SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
#    PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
#    USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT
#    LIMITED TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR
#    MAKES NO WARRANTY AND HAS NO LIABILITY ARISING FROM ANY USE OF THE
#    SOFTWARE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITIES.

'''This is an initial attempt at logging GPI sessions.  Currently all logging
information is printed to stdout b/c there is a missing mechanism to
communicate logging statements back from forked processes. '''

import time
import inspect
import logging

GPINODE = logging.INFO + 1
DIALOG = logging.CRITICAL + 1

# A more thread safe replacement for the std::logging package.
# At the time this was written there were errors in threaded modules:
#  Exception AttributeError: AttributeError("'_DummyThread' object has no attribute '_Thread__block'",) in <module 'threading' from '/opt/local/Library/Frameworks/Python.framework/Versions/2.7/lib/python2.7/threading.pyc'> ignored  
# Just using the print command to stdout works for this application without the
# added errors. -This will need to be fixed if log files are implemented.
class PrintLogger(object):
    def __init__(self, name):
        self._name = name
        self._level = logging.WARNING

    def setLevel(self, lev):
        self._level = lev

    def debug(self, msg):
        if self._level <= logging.DEBUG:
            self.printb(msg, 'DEBUG')

    def info(self, msg):
        if self._level <= logging.INFO:
            self.printb(msg, 'INFO')

    def node(self, msg):
        if self._level <= GPINODE:
            self.printb(msg, 'NODE')

    def warn(self, msg):
        if self._level <= logging.WARNING:
            self.printb(msg, 'WARNING')

    def error(self, msg):
        if self._level <= logging.ERROR:
            self.printb(msg, 'ERROR')

    def critical(self, msg):
        if self._level <= logging.CRITICAL:
            self.printb(msg, 'CRITICAL')

    def dialog(self, msg):
        # things marked with dialog should eventually get a popup dialog box
        # to actually interact with.  This is just a reminder.
        if self._level <= DIALOG:
            self.printb(msg, '----')

    def printb(self, msg, lev):
        # get the line number by getting the current frame (printb()) then
        # going back to (debug(), info(), warn(), etc...), then back once
        # more to where the logger was called.
        lineno = str(inspect.currentframe().f_back.f_back.f_lineno)

        # the user input 'msg' is forced to be a string
        print((time.asctime(time.localtime()) + ' - ' + self._name + ':' + lineno + ' - ' + lev + ' - ' + str(msg)))


class GPILogManager(object):
    def __init__(self):
        # From: http://docs.python.org/2/howto/logging.html

        # default level, keep loggers on full
        self.default_level = logging.DEBUG

        # default level, start console on mid
        self.console_level = logging.WARNING

        # create logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.default_level)

        # create console handler and set level to debug
        #self.ch = logging.NullHandler()  # Turn completely off
        self.ch = logging.StreamHandler()
        self.ch.setLevel(self.console_level)

        # create formatter
        self.formatter = logging.Formatter(
            '%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s')

        # add formatter to ch
        self.ch.setFormatter(self.formatter)

        # add ch to logger
        self.logger.addHandler(self.ch)

    def getLogger(self, name):
        # automatically attach it to the console handle
        logger = logging.getLogger(name)
        logger.addHandler(self.ch)
        logger.setLevel(self.default_level)
        return logger

    def setLevel(self, lev):
        # set the console level
        self.ch.setLevel(lev)
        self.console_level = lev

    def isDebug(self):
        return self.console_level <= logging.DEBUG
    def isWarning(self):
        return self.console_level <= logging.WARNING
    def isInfo(self):
        return self.console_level <= logging.INFO
    def isError(self):
        return self.console_level <= logging.ERROR
    def isCritical(self):
        return self.console_level <= logging.CRITICAL

    def getMainLogger(self):
        return self.logger


class GPIPrintManager(GPILogManager):

    def __init__(self):
        super(GPIPrintManager, self).__init__()
    
        self.logger = PrintLogger(__name__)
        self.logger.setLevel(self.console_level)

        self.loggers = []

    def getLogger(self, name):
        logger = PrintLogger(name)
        logger.setLevel(self.console_level)
        self.loggers.append(logger)
        return logger

    def setLevel(self, lev):
        super(GPIPrintManager, self).setLevel(lev)

        for logger in self.loggers:
            logger.setLevel(lev)

    def getMainLogger(self):
        return self.logger

# global handles
#manager = GPILogManager()
manager = GPIPrintManager()
logger = manager.getMainLogger()

# default log level
manager.setLevel(logging.WARNING)

# 'application' code
# logger.debug('debug message')
# logger.info('info message')
# logger.warn('warn message')
# logger.error('error message')
# logger.critical('critical message')
#
# manager.setLevel(logging.CRITICAL)
#
# logger.info('after switch')
#
# manager.setLevel(logging.DEBUG)
