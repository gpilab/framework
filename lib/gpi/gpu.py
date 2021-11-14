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


import rpyc
from rpyc.utils.server import ThreadedServer
from gpi import QtCore
from .logger import manager

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
        server = ThreadedServer(service, port=18861)
        t = threading.Thread(target = server.start)
        t.daemon = True
        t.start()
        print("Server Side")
        return service
    except:
        print("Client Side")
        return None

def run_on_gpu_server(func):
    def wrapper(*args, **kwargs):
        c = rpyc.connect("localhost", 18861)
        result = c.root.compute_func(func, *args, **kwargs)
        return result
    wrapper.func = func
    return wrapper


# def run_image(canvas):
#     pos = QtCore.QPoint(50, 35)
#     item = item = canvas._library.findNode_byName('ImageViewer')
#     print(item)
#     node = canvas.newNode_byNodeCatalogItem(item, pos)
#     compute = node._nodeIF.compute.func
#     node._nodeIF.compute = lambda: compute(node._nodeIF)
#     node.computeRun("compute")
#     print(node.inportList[0].portTitle)
#             # node._machine.start(node._computeState)
#             # node._nodeIF.compute(node._nodeIF)




# class RPyCServer(QtCore.QObject):
#     """ Contains a RPyC server that serves modules to remote computers. Runs in a QThread.
#     """
#     def __init__(self, service, host, port):
#         """
#           @param class serviceClass: class that represents an RPyC service
#           @param int port: port that hte RPyC server should listen on
#         """
#         super().__init__()
#         self.service = service
#         self.host = host
#         self.port = port

#     def run(self):
#         """ Start the RPyC server
#         """
#         print("running")
#         self.server = ThreadedServer(self.service, hostname=self.host, port=self.port)
        
#         self.server.start()

# class MyService(rpyc.Service):
#     def __init__(self, canvas) -> None:
#         super().__init__()
#         self.canvas = canvas
#         print(self.canvas)
#     def on_connect(self, conn):
#         pass

#     def on_disconnect(self, conn):
#         pass

#     def exposed_compute_on_gpu(self):
#         print(self.canvas)
#         canvas = self.canvas
#         pos = QtCore.QPoint(50, 35)
#         item = item = canvas._library.findNode_byName('ImageViewer')
#         print(item)
#         node = Node(canvas, nodeCatItem=item)
#         compute = node._nodeIF.compute.func
#         print("compute func:", compute)
#         # node._nodeIF.compute = lambda: compute(node._nodeIF)
#         # node.computeRun("compute")
#         # print(node.inportList[0].portTitle)
#         # # node._machine.start(node._computeState)
#         # # node._nodeIF.compute(node._nodeIF)
#         return self.canvas

# class RPyCServer(QtCore.QThread):

#     def __init__(self, service, host=None, port=None):
#         super(RPyCServer, self).__init__()
#         self._server = Server(service, port=port)
#         self.run = self._server.start

# class Remote_Server(QtCore.QObject):
#     sig = QtCore.Signal(str)
#     def __init__(self, canvas) -> None:
#         super().__init__()
#         self.canvas = canvas
        
#     def run_server(self, canvas):
#         self.thread = RPyCServer(self.create_service(canvas), port=18861)
#         self.thread.start()
    
#     def create_service(self, canvas):
#         class Service(rpyc.Service):
#             def on_connect(self, conn):
#                 pass

#             def on_disconnect(self, conn):
#                 pass

#             def exposed_compute_on_gpu(self):
#                 print(self.canvas)
#                 canvas = canvas
#                 pos = QtCore.QPoint(50, 35)
#                 item = canvas._library.findNode_byName('ImageViewer')
#                 print(item.key())
#                 self.sig.emit(item.key())

#                 # node = Node(canvas, nodeCatItem=item)
#                 compute = node._nodeIF.compute.func
#                 print("compute func:", compute)
#                 # node._nodeIF.compute = lambda: compute(node._nodeIF)
#                 # node.computeRun("compute")
#                 # print(node.inportList[0].portTitle)
#                 # # node._machine.start(node._computeState)
#                 # # node._nodeIF.compute(node._nodeIF)
#                 return self.canvas

#         return Service
    
#     # def run_server(self, canvas):
#     #     self.server = RPyCServer(self.create_service(canvas) ,host="localhost", port=18861)
#     #     self.server.moveToThread(self.thread)
#     #     self.thread.started.connect(self.server.run)
#     #     self.thread.start()
#     #     print("here")



# def lol(canvas):
#     try:
#         server = Remote_Server(canvas)
#         return server
#         print("cool")
#     except:
#         print("didnt run server")
#         pass

# server = Remote_Server(None)
# run_server = server.run_server
# server.sig.connect(lambda x: print(x))