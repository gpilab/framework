# GPI (v1.5.0) auto-generated library file.
#
# FILE: C:/Users/310217414/Documents/SW\my_nodes\simple\GPI\my_nodes_GPI.py
#
# For node API examples (i.e. widgets and ports) look at the
# core.interfaces.Template node.

import time
import gpi

class ExternalNode(gpi.NodeAPI):
    '''Iterates N steps and simulates 5 seconds of total processing time.
    '''

    def initUI(self):

        return 0

    def compute(self):

        num_iter = 20
        total_duration = 5.0  # seconds to simulate

        step_duration = total_duration / num_iter

        for i in range(num_iter):
            # Perform CPU-bound work for roughly step_duration seconds.
            start = time.perf_counter()
            value = 0.0
            while time.perf_counter() - start < step_duration:
                # Intense arithmetic work to keep the CPU busy.
                value += (value * 1.0000001 + 3.14159265) ** 2
                value %= 1e9

            progress = int((i + 1) / num_iter * 100)

        return 0
