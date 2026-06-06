# Author: Ashley Anderson
# Date: 2015-12-18 13:36

import gpi
import os
import shutil
import tempfile
import urllib.request

class ExternalNode(gpi.NodeAPI):
    """This node will download a file and save it to the disk. If the file is a
    recognized format, the data can then be read into GPI using one of the
    readers in core.fileIO.

    OUTPUT:
        path - local filepath for the downloaded file
    WIDGETS:
        url - the URL of the file you want to download
        save local copy - if enabled, you can choose the path to save the file,
            otherwise it will be saved to a temp file
        save file - where to save the file
        re-download - download the file again, even if it is stored locally
    """

    # initialize the UI - add widgets and input/output ports
    def initUI(self):
        # Widgets
        self.addWidget('StringBox', 'url', placeholder="https://www.gpilab.com/example_data.npy")
        self.addWidget('PushButton', 'save local copy', toggle=True, val=False)
        self.addWidget('SaveFileBrowser', 'save file', button_title='Browse')
        self.addWidget('PushButton', 're-download')

        self.addWidget('PushButton', 'validate', toggle=True, val=False, visible=False)
        self.addWidget('StringBox', 'checksum', visible=False)

        # IO Ports
        self.addOutPort('path', 'STRING')

        self.url = None

    # validate the data - runs immediately before compute
    # your last chance to show/hide/edit widgets
    # return 1 if the data is not valid - compute will not run
    # return 0 if the data is valid - compute will run
    def validate(self):
        if self.getVal('save local copy'):
            self.setAttr('save file', visible=True)
        else:
            self.setAttr('save file', visible=False)

        # don't overwrite an existing file
        if os.path.exists(self.getVal('save file')):
            self.log.error("For safety, this node will not overwrite existing "
                           + "files. ")
            self.log.error("If you really want to overwrite the file "
                           + self.getVal('save file')
                           + " please delete it manually.")
            return 1

        # clear the path if the URL has changed
        # this will cause a re-download when the URL is changed
        if self.url != self.getVal('url'):
            self.setData('path', None)
            self.url = self.getVal('url')

        if self.url:
            self.setDetailLabel(self.url)

        return 0

    # process the input data, send it to the output port
    # return 1 if the computation failed
    # return 0 if the computation was successful
    def compute(self):
        # logic regarding when to skip the download
        if not (self.getData('path') is None
                or 're-download' in self.widgetEvents()):
            if self.getVal('save local copy') and 'save file' in self.widgetEvents():
                try:
                    shutil.copyfile(self.getData('path'), self.getVal('save file'))
                    self.setData('path', self.getVal('save file'))
                except OSError as e:
                    self.log.error("Couldn't copy temp file to "
                                   + self.getVal('save file')
                                   + " Try re-downloading.")
            return 0

        # prevent the node from running when first instantiated
        if self.url is None or self.url == '':
            return 0

        self.log.info("Downloading file from: {}".format(self.url))
        try:
            R = urllib.request.urlopen(self.url)
        except ValueError as e:
            self.log.error("Unknown URL type."
                           + "Make sure it starts with the protocol"
                           + "e.g. 'http://'.")
            return 1

        fp = None
        if self.getVal('save local copy'):
            try:
                fp = open(self.getVal('save file'), 'w+b')
            except FileNotFoundError:
                self.log.warn("File path " + self.getVal('save file')
                              + "not available. "
                              +"Saving to a temporary file instead.")
        if fp is None:
            fp = tempfile.NamedTemporaryFile(delete=False)

        # here is where the data is actually downloaded (may take a while)
        fp.write(R.read())
        fp.close()

        out = fp.name
        self.setData('path', out)

        return 0

    def execType(self):
        return gpi.GPI_THREAD
