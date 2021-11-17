#    Copyright (C) 2021 Mayo Clinic
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

from __future__ import print_function

import rpyc
from rpyc.utils.server import ThreadedServer
from gpi import QtCore
from .logger import manager
# rpyc.core.protocol.DEFAULT_CONFIG['allow_pickle'] = True


# start logger for this module
log = manager.getLogger(__name__)

class Service(rpyc.Service, QtCore.QObject):
    sig = QtCore.Signal(bytes)

    def on_connect(self, conn):
        pass

    def on_disconnect(self, conn):
        pass

    def exposed_compute_on_gpu(self, binary_data:bytes):
        """Receive the node name to compute and its necessary data in dill serialized format

            Args:
                binary_data(bytes): Serialized information needed to execute the node compute function
        """
        self.sig.emit(binary_data)
        return
    
    def exposed_compute_func(self, func, *args, **kwargs):
        print("Server func:", func)
        print("Server args:", *args)
        print("Server kwargs:", **kwargs)
        result = func(*args, **kwargs)
        print("result:", result)
        return result





def run_gpu_server():
    "Run the gpu server to do computations on"
    try:
        import threading
        service = Service()
        server = ThreadedServer(service, hostname="archimedes.mayo.edu", port=18861)
        t = threading.Thread(target = server.start)
        t.daemon = True
        t.start()
        print("Server Side")
        return service
    except:
        print("Client Side")
        return None

# def factory(f, *args, **kwargs):
#     def f (*args, **kwargs):
#         import cupy as np
#         return f(*args, **kwargs)
#     return f

import time
import dill
import zlib


import logging

import grpc
from . import gpi_pb2
from . import gpi_pb2_grpc
import dill
import zlib
dill.settings['recurse'] = True

options = [
        ('grpc.max_send_message_length', 2**30),
        ('grpc.max_receive_message_length', 2**30),
    ]

import time
def run(f, args):
    channel = grpc.insecure_channel('archimedes.mayo.edu:50051', options=options)
    stub = gpi_pb2_grpc.GPIStub(channel)
    func = dill.dumps(f)
    args = dill.dumps(args)
    start = time.time()
    response = stub.run(gpi_pb2.Request(function=func, args=args))
    end = time.time()
    print(end- start)
    return dill.loads(response.result)

def run_on_gpu_server(func):
    def wrapper(*args, **kwargs):
        result = run(func, args)
        return result
    wrapper.func = func
    return wrapper