#!/usr/bin/env python
# Author: Nick Zwart
# Date: 2016mar25
# Query a conda package index for the latest version.

import subprocess
import json

conda = 'conda'
channel = 'http://conda.anaconda.org/gpi'
package = 'gpi'

def get():
    gpi_pkgs = subprocess.Popen('%s search --override-channels --channel %s -f \
            %s --json' % (conda,channel,package), shell=True,
            stdout=subprocess.PIPE).stdout.read().decode('ascii')
    gpi_pkgs = json.loads(gpi_pkgs)
    return max([ ver['version'] for ver in gpi_pkgs['gpi']])

if __name__ == '__main__':
    print(get())
