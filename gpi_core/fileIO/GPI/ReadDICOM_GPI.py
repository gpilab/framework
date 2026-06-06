# Author: Ryan Robison
# Date: 2017 Jul 12

import os
import gpi

class ExternalNode(gpi.NodeAPI):
    """Read in all Dicom data from a file

    OUTPUT: Dicom images from file

    WIDGETS:
    I/O Info - Gives info on data file and data type
    File Browser - button to launch file browser, and typein widget if the pathway is known.
    """

    def execType(self):
        # default executable type
        # return gpi.GPI_THREAD
        return gpi.GPI_PROCESS # this is the safest
        # return gpi.GPI_APPLOOP

    def initUI(self):

        # Widgets
        self.addWidget('TextBox', 'I/O Info:')
        self.addWidget('OpenFileBrowser', 'File Browser',
                button_title='Browse', caption='Open File',
                filter='(DICOMDIR IM* *.dcm)')
        self.addWidget('ComboBox', 'Series', items=[])
        self.addWidget('PushButton', 'Read All', toggle = True, val=0)
        self.addWidget('PushButton', 'De-Identify on Read', toggle = True, val=0)
        self.addWidget('PushButton', 'Read', toggle = True, val=0)

        # IO Ports
        self.addOutPort(title='out', type='NPYarray')
        self.addOutPort(title='DicomDict', type='DICT')

        self.URI = gpi.TranslateFileURI

    def validate(self):
        import gpi_core.fileIO.dicomlib as dcm
        #import imp
        fname = self.URI(self.getVal('File Browser'))
        self.setDetailLabel(fname)
        #imp.reload(dcm)

        # check that the path actually exists
        if not os.path.exists(fname):
            self.log.node("Path does not exist: "+str(fname))
            return 0

        base = os.path.basename(fname)
        if base == 'DICOMDIR':
            self.setAttr('Read All', visible=False)
        else:
            self.setAttr('Read All', visible=True)

        #parse DICOMDIR file to get series info
        if ('File Browser' in self.widgetEvents()):
            if base == 'DICOMDIR':
                info = dcm.get_series_info(fname)
                series_list = ["{} :: {}".format(s, p) for s, p in zip(info['series'], info['protocol'])]
                self.setAttr('Series', items = series_list, visible=True)
            else:
                self.setAttr('Series', visible=False)


    def compute(self):

        import os
        import time
        import re
        import gpi_core.fileIO.dicomlib as dcm

        # start file browser
        fname = self.URI(self.getVal('File Browser'))
        read = self.getVal('Read')
        readall = self.getVal('Read All')
        anonymize = self.getVal('De-Identify on Read')
        series = self.getVal('Series')
        dicomDict = {}

        if read:
            base = os.path.basename(fname)
            directory = os.path.dirname(fname)
            # generate list of dicom files to read
            if base == 'DICOMDIR':
                series_num = re.split('::',series)[0]
                dicomFileList = dcm.gen_dicom_list(fname, series_num)
                # change to DICOM folder if DICOMDIR
                fname = directory+'/DICOM'
            elif readall:
                dicomFileList = dcm.dicom_file_list(directory)
            else:
                dicomFileList = [fname]

            # show some file stats
            fstats = os.stat(fname)
            # creation
            ctime = time.strftime('%d/%m/20%y', time.localtime(fstats.st_ctime))
            # mod time
            mtime = time.strftime('%d/%m/20%y', time.localtime(fstats.st_mtime))
            # access time
            atime = time.strftime('%d/%m/20%y', time.localtime(fstats.st_atime))
            # filesize
            fsize = fstats.st_size
            # user id
            uid = fstats.st_uid
            # group id
            gid = fstats.st_gid

            # read the data
            out, dicomDict = dcm.load_dicom(dicomFileList, anonymize)
            d1 = list(out.shape)
            info = "created: "+str(ctime)+"\n" \
                   "accessed: "+str(atime)+"\n" \
                   "modified: "+str(mtime)+"\n" \
                   "UID: "+str(uid)+"\n" \
                   "GID: "+str(gid)+"\n" \
                   "file size (bytes): "+str(fsize)+"\n" \
                   "dimensions: "+str(d1)+"\n" \
                   "type: "+str(out.dtype)+"\n"
            self.setAttr('I/O Info:', val=info)

        else:
            out = None

        self.setData('out', out)
        if (len(dicomDict) > 0):
            self.setData('DicomDict', dicomDict)

        return(0)
