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

import time
import grpc
import dill
from . import gpi_pb2
from . import gpi_pb2_grpc
from .logger import manager
dill.settings['recurse'] = True

# start logger for this module
log = manager.getLogger(__name__)

options = [
        ('grpc.max_send_message_length', -1),
        ('grpc.max_receive_message_length', -1),
        ("grpc.so_reuseport", 1),
        ("grpc.use_local_subchannel_pool", 1),
    ]

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

def run_on_server(function=None, parallel=False):
    from gpi import parallel as par
    def decorator(func):
        def wrapper(*args, **kwargs):
            if parallel:
                result = par.function(run)(func, args)
            else:
                result = run(func, args)
            return result
        wrapper.func = func
        return wrapper
    if function: return decorator(function)
    return decorator