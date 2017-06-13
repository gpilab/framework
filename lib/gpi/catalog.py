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

# Brief: A simple data mapping structure.

# gpi
from .logger import manager

# start logger for this module
log = manager.getLogger(__name__)


class CatalogObj(object):
    '''An abstract object to be used with the Catalog indexing object.
    '''
    def __init__(self):
        # save relevant info
        pass
    def key(self):  
        # -used in dict and held for reverse lookup
        # -sorted against
        # -unique identifier (collisions will cause a merge)
        # -should be the most likely search for the contained data since it
        #   will be the fasted lookup
        # return a string
        pass
    def merge(self, e):
        # collisions can be used to add extra data
        pass
    def __str__(self):
        # stringify internal data for printing
        # return a string
        pass

class Catalog(object):
    '''A generic catalog object for referencing/indexing/sorting a list of
    descriptions based on their content.  Mostly just an extra interface to a
    dictionary that allows information merges.  Keys are determined by the
    appended object.
    '''

    def __init__(self):
        self._db = {}  # a hash of objects

    def __len__(self):
        return len(self._db)

    def append(self, elem):

        # merge data if this id already exists
        if elem.key() in self._db:
            self._db[elem.key()].merge(elem)
        else:
            self._db[elem.key()] = elem

    def keys(self):
        return list(self._db.keys())

    def values(self):
        return list(self._db.values())

    def iteritems(self):
        return iter(list(self._db.items()))

    def d(self):
        return self._db

    def __str__(self):
        o = '\n'
        for k,v in list(self._db.items()):
            o += k +': '+str(v) + '\n'
        return o

    def get(self, key):
        return self._db[key]

    def find(self, attr, value):
        # return the first object with the given attribute and value
        for k,v in list(self._db.items()):
            if hasattr(v, attr):
                if getattr(v, attr) == value:
                    return v

    def list(self, attr, value):
        o = []
        # return a list of objects with the given attribute and value
        for k,v in list(self._db.items()):
            if hasattr(v, attr):
                if getattr(v, attr) == value:
                    o.append(v)
        if len(o) > 0:
            return o
        else:
            return None

    def intrafind(self, finder, key):
        # Return the first object with a True internal finder() result.
        # The finder() function is a method contained within the CatalogObj()
        # subclass that returns True or False given the passed key for comparison.
        for k,v in list(self._db.items()):
            if hasattr(v, finder):
                if getattr(v, finder)(key):
                    return v

    def intralist(self, finder, key):
        # Return a list of objects with a True internal finder() result.
        # The finder() function is a method contained within the CatalogObj()
        # subclass that returns True or False given the passed key for comparison.
        o = []
        for k,v in list(self._db.items()):
            if hasattr(v, finder):
                if getattr(v, finder)(key):
                    o.append(v)
        if len(o) > 0:
            return o
        else:
            return None
