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

# External Binary Encapsulation
#   This is a set of convenience functions for wrapping external binaries in
#   python.

import os
import hashlib
import subprocess
import numpy as np

# gpi
from .defines import GPI_SHDM_PATH
from .logger import manager
from .sysspecs import Specs

# start logger for this module
log = manager.getLogger(__name__)


class FilePath(object):
    '''Generate a tempfile-name and path based on THIS object's id.  If THIS
    object looses its reference then make sure the associated file is also
    deleted. The supplied read/writer functions can be used to write and
    retrieve the file information. If a tempfile-path and name is all that is
    needed, then this object can be instantiated without any arguments.

    path: /tmp (default GPI tmp dir)
    filename: additional to the nodeid
    suffix: additional to the nodeid (i.e. '.jpg')
    nodeid: node's location in memory (id())
    rfunc: reader function with footprint:
                data = rfunc('filename')
    wfunc: writer function with footprint:
                retcode = wfunc('filename', data)
                retcode: None or 0 for success

    If no names are specified then THIS object id is used.
    '''
    _Extern_File_Handle_Type = True

    def __init__(self, wfunc=None, wdata=None, path=None, filename=None,
                 suffix=None, nodeid=None, rfunc=None, asuffix=[]):

        self._reader = rfunc
        self._writer = wfunc
        self._output_data = wdata # data to be written

        self._suffix = ''
        if suffix is not None:
            self._suffix = suffix

        self._additional_suffix = set(asuffix + [self._suffix, '']) - set([None])

        ## build the filepath one step at a time

        self._basename_path = ''
        self._filename = ''
        if nodeid:
            self._filename += str(nodeid)

        if filename:
            if self._filename != '':
                self._filename += '_'
            self._filename += str(filename)

        # just use THIS object id if nothing is specified
        if self._filename == '':
            self._filename = str(id(self))

        if path:
            self._basename_path = os.path.join(str(path), self._filename)
        else:
            self._basename_path = os.path.join(GPI_SHDM_PATH, self._filename)

        if self._suffix:
            self._filename += self._suffix

        if self.fileExists():
            log.warn('The path: \'' + self._basename_path + '\' already exists, continuing...')

    def __str__(self):
        return self._basename_path

    def __del__(self):
        # this may not delete in a timely fashion so direct use of clear() is
        # encouraged.
        if self.fileExists():
            log.warn('The \'FilePath\' object for path: \''+self._basename_path+'\' was not closed before collection.')
            self.clear()

    def additionalSuffix(self, suf=[]):
        # in case the filename is used as a basename, this will allow more
        # files to be searched for removal.  -helpful for formats that require
        # multiple files.
        self._additional_suffix = suf

    def clear(self):
        for s in self._additional_suffix:
            if os.path.isfile(self._basename_path + s):
                os.remove(self._basename_path + s)

    def fileExists(self):
        for s in self._additional_suffix:
            if os.path.isfile(self._basename_path + s):
                return True
        return False

    def close(self):
        self.clear()

    def setReader(self, func):
        self._reader = func

    def setWriter(self, func):
        self._writer = func

    def read(self, suffix=None):
        if suffix is None:
            suffix = self._suffix
        return self._reader(self._basename_path + suffix)

    def data(self, suffix=None):
        if suffix is None:
            suffix = self._suffix
        return self.read(suffix)

    def write(self, suffix=None):
        if suffix is None:
            suffix = self._suffix
        return self._writer(self._basename_path + suffix, self._output_data)

    def isOutput(self):
        # this file is the result of running the command
        if self._reader:
            return True
        return False

    def isInput(self):
        # this file is an input argument to the command
        if self._writer:
            return True
        return False

class IFilePath(FilePath):
    def __init__(self, wfunc, wdata, suffix=None, asuffix=[]):
        super(IFilePath, self).__init__(wfunc=wfunc, wdata=wdata, suffix=suffix, asuffix=asuffix)

class OFilePath(FilePath):
    def __init__(self, rfunc, suffix=None, asuffix=[]):
        super(OFilePath, self).__init__(rfunc=rfunc, suffix=suffix, asuffix=asuffix)

class Command(object):
    '''This object simplifies the situation where an external program generates
    a file and potentially takes a file as input.  These files need to be
    communicated as commandline arguments, and also need to be read and written
    from gpi.

    in1 = FilePath('.cfl', writer, data)
    out1 = FilePath('.cfl', reader)

    # run command immediatly
    Command('fft', in1, '-o', out1, '-d1')

    # setup a command list
    c = Command()
    c.arg('fft')
    c.arg(in1, '-o', out1)
    c.arg('-d1')
    c.run()

    data = out1.read()
    '''

    def __init__(self, *args, **kwargs):

        self._warn = True
        if 'warn' in kwargs:
            self._warn = kwargs['warn']

        self._checkForInvalidArgs(args)
        self._cmd = args

        self._retcode = None
        if len(self._cmd):
            # run the command straight away if there is one
            self._retcode = self.run()

    def _checkForInvalidArgs(self, args):
        for a in args:
            if type(a) not in [OFilePath, IFilePath, FilePath, str]:
                types = [type(a) for a in args]
                raise ValueError('Command:Args must be of type str, OFilePath, IFilePath or FilePath. '+str(types))

    def arg(self, *args):
        self._checkForInvalidArgs(args)
        self._cmd += args

    def setWarning(self, val):
        self._warn = val

    def returnCode(self):
        return self._retcode

    def __str__(self):
        # this is the actual command that is passed to subprocess
        return ' '.join([str(x) for x in self._cmd])

    def getArgList(self):
        return self._cmd

    def getArgString(self):
        return str(self)

    def run(self):

        # write all data to input files
        for x in self._cmd:
            if hasattr(x, '_Extern_File_Handle_Type'):
                if x.isInput():
                    x.write()

        # run the command
        self._retcode = subprocess.check_call(str(self), shell=True)
        return self._retcode
