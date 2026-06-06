# Copyright (c) 2014, Dignity Health
# 
#     The GPI core node library is licensed under
# either the BSD 3-clause or the LGPL v. 3.
# 
#     Under either license, the following additional term applies:
# 
#         NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL
# PURPOSES AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
# SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
# PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
# USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT LIMITED
# TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR MAKES NO
# WARRANTY AND HAS NOR LIABILITY ARISING FROM ANY USE OF THE SOFTWARE IN ANY
# HIGH RISK OR STRICT LIABILITY ACTIVITIES.
# 
#     If you elect to license the GPI core node library under the LGPL the
# following applies:
# 
#         This file is part of the GPI core node library.
# 
#         The GPI core node library is free software: you can redistribute it
# and/or modify it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version. GPI core node library is distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Lesser General Public License for more details.
# 
#         You should have received a copy of the GNU Lesser General Public
# License along with the GPI core node library. If not, see
# <http://www.gnu.org/licenses/>.

# Author: Nick Zwart
# Date: 2013aug16

import gpi


class ExternalNode(gpi.NodeAPI):
    """Browse the web for data, search your local subversion repo for code
    hints, or update the GPI wiki.
    """

    def initUI(self):
        # Widgets
        self.addWidget('StringBox', 'URL', val='http://')
        self.addWidget('WebBox', 'WebBrowser', val='www.google.com')
        self.addWidget('ComboBox','GPI Bookmarks', items=['Bug Tracker','Wiki','Share','Share Uploader','Repository'])
        self.addWidget('StringBox', 'Username/Login')
        self.addWidget('StringBox', 'Password', mask=True)

    def validate(self):

        events = self.widgetEvents()
        if 'URL' in events:
            self.log.info(self.getVal('URL'))
            self.setAttr('WebBrowser', val=self.getVal('URL'), passwd=None, username=None)

        elif 'GPI Bookmarks' in events:
            mark = self.getVal('GPI Bookmarks')
            #base = 'http://mbl1:5555'
            base = 'http://cylon'
            if mark == 'Bug Tracker':
                url = base+'/trac'
            if mark == 'Wiki':
                url = base+'/wiki'
            if mark == 'Share':
                url = base+'/share'
            if mark == 'Share Uploader':
                url = base+'/ajaxplorer'
            if mark == 'Repository':
                url = base+'/svn'
            self.setAttr('WebBrowser', val=url)

        elif 'Username/Login' in events:
            self.setAttr('WebBrowser', username=self.getVal('Username/Login'))

        elif 'Password' in events:
            self.setAttr('WebBrowser', passwd=self.getAttr('Password', 'maskedval'))

        elif 'WebBrowser' in events:
            url = self.getVal('WebBrowser')
            self.setAttr('URL', val=url)

        return 0

    def execType(self):
        return gpi.GPI_THREAD
