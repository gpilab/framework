"""Write numpy arrays to a MATLAB MAT-file."""

import os
import re
import tempfile

import gpi


class ExternalNode(gpi.NodeAPI):
    """Write up to five named arrays to a MATLAB level-5 .mat file.

    File Browser, Write Mode and Write Now behave like WriteNPY. Connected
    inputs use their Array Name as MATLAB variables. Names must start with
    a letter and contain only ASCII letters, digits or underscores (max 63).
    Complex data and multidimensional shapes are preserved; 1D arrays become
    MATLAB row vectors. Compression is optional. This is not HDF5/v7.3 format;
    the level-5 per-variable size limit applies (approximately 2 GB).
    """

    def initUI(self):
        self.addWidget('SaveFileBrowser', 'File Browser', button_title='Browse',
                       caption='Save MATLAB File', filter='MATLAB (*.mat)')
        self.addWidget('PushButton', 'Write Mode',
                       button_title='Write on New Filename', toggle=True)
        self.addWidget('PushButton', 'Write Now', button_title='Write Right Now', toggle=False)
        self.addWidget('PushButton', 'Compression', toggle=True, val=True)
        for port in ('in', 'in2', 'in3', 'in4', 'in5'):
            self.addWidget('StringBox', 'Array Name ({})'.format(port), val=port)
        self.addInPort('in', 'NPYarray')
        for index in range(2, 6):
            self.addInPort('in{}'.format(index), 'NPYarray', obligation=gpi.OPTIONAL)
        self.URI = gpi.TranslateFileURI

    def validate(self):
        title = 'Write on Every Event' if self.getVal('Write Mode') else 'Write on New Filename'
        self.setAttr('Write Mode', button_title=title)
        self.setDetailLabel(self.URI(self.getVal('File Browser')))
        for port in ('in', 'in2', 'in3', 'in4', 'in5'):
            self.setAttr('Array Name ({})'.format(port), visible=self.getData(port) is not None)
        return 0

    def compute(self):
        from scipy.io import savemat
        from scipy.io.matlab import MatWriteError

        if not (self.getVal('Write Mode') or self.getVal('Write Now')
                or 'File Browser' in self.widgetEvents()):
            return 0
        fname = self.URI(self.getVal('File Browser'))
        if not fname:
            return 0
        if not fname.lower().endswith('.mat'):
            fname += '.mat'
            self.setAttr('File Browser', val=fname)
            self.setDetailLabel(fname)
        arrays = {}
        keywords = {'break', 'case', 'catch', 'classdef', 'continue', 'else', 'elseif',
                    'end', 'for', 'function', 'global', 'if', 'otherwise', 'parfor',
                    'persistent', 'return', 'spmd', 'switch', 'try', 'while'}
        for port in ('in', 'in2', 'in3', 'in4', 'in5'):
            data = self.getData(port)
            if data is None:
                continue
            name = self.getVal('Array Name ({})'.format(port)).strip()
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,62}', name) or name in keywords:
                self.log.error('WriteMAT: invalid MATLAB variable name {!r}'.format(name))
                return 1
            if name in arrays:
                self.log.error('WriteMAT: duplicate variable name {!r}'.format(name))
                return 1
            arrays[name] = data
        if not arrays:
            self.log.error('WriteMAT: no arrays connected.')
            return 1
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=os.path.dirname(os.path.abspath(fname)),
                                             suffix='.mat', delete=False) as output:
                temporary = output.name
                savemat(output.file, arrays, appendmat=False, format='5',
                        do_compression=bool(self.getVal('Compression')), oned_as='row')
            os.replace(temporary, fname)
        except (OSError, ValueError, TypeError, NotImplementedError, MatWriteError) as error:
            self.log.error('WriteMAT: {}'.format(error))
            return 1
        finally:
            if temporary is not None and os.path.exists(temporary):
                os.unlink(temporary)
        return 0