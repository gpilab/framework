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

from dataclasses import dataclass, field
from typing import Dict, Any
import numpy as np

@dataclass
class MRIData:
    """
    A dataclass to store and manage MRI data and its associated parameters.

    Attributes:
        idata (np.ndarray): Complex float array representing k-space data.
        coords (np.ndarray): Float array representing coordinates.
        coords_cg (np.ndarray): Float array representing constant gradient coordinates.
        sdc (np.ndarray): Float array representing sampling density compensation.
        sdc_cg (np.ndarray): Float array representing constant gradient sampling density compensation.
        tmap (np.ndarray): Float array representing the Time map.
        data_params (Dict[str, Any]): Dictionary containing local metadata specific to this object.
    """
    idata: np.ndarray  # Complex float (np.complex64 or np.complex128)
    coords: np.ndarray  # Float (np.float32 or np.float64)
    coords_cg: np.ndarray  # Float (np.float32 or np.float64)
    sdc: np.ndarray  # Float (np.float32 or np.float64)
    sdc_cg: np.ndarray  # Float (np.float32 or np.float64)
    tmap: np.ndarray  # Float (np.float32 or np.float64)
    data_params: Dict[str, Any] = field(default_factory=lambda: {
        "trajectory": "Spiral",  # Trajectory type: Spiral, FLORET, Cartesian, Radial, PROPELLER
        "type": "SE",  # Sequence type: Spin Echo or Gradient Echo
        "space": "kspace",  # space: kspace, ispace
        "tau": 10.0,  # readout duration in msec
        "axes_labels": [],  # Array of strings specifying what each axis represents
        "echo_times": [],  # Echo times in ms
        "extra_params": {}  # Dictionary for extra parameters
    })

    def update_params(self, data_type: str, echo_times: np.ndarray, axes_labels: list, space: str, tau: float, trajectory: str = "Spiral", extra_params: dict = None):
        """
        Update global and local parameters for the MRIData object.

        Args:
            data_type (str): String specifying the data type (e.g., "SE").
            echo_times (np.ndarray): 2D NumPy array of echo times in ms.
            axes_labels (list): List of strings specifying what each axis represents.
            space (str): String specifying the space type (e.g., "kspace").
            tau (float): Readout duration in msec.
            trajectory (str): String specifying the trajectory type (e.g., "Spiral").
            extra_params (dict): Dictionary for extra parameters.
        """
        self.data_params["type"] = data_type
        self.data_params["echo_times"] = echo_times
        if len(axes_labels) != self.idata.ndim:
            raise ValueError(f"Length of axes_labels ({len(axes_labels)}) must match the number of dimensions of idata ({self.idata.ndim})")
        self.data_params["axes_labels"] = axes_labels
        self.data_params["space"] = space
        self.data_params["tau"] = tau
        self.data_params["trajectory"] = trajectory
        if extra_params is not None:
            self.data_params["extra_params"] = extra_params
            
        

# Example usage
if __name__ == "__main__":
    # Create sample data
    data = np.zeros((128, 128), dtype=np.complex64)
    coords = np.zeros((128, 2), dtype=np.float32)
    coords_cg = np.zeros((128, 2), dtype=np.float32)
    sdc = np.ones((128,), dtype=np.float32)
    sdc_cg = np.ones((128,), dtype=np.float32)
    tmap = np.zeros((128, 128), dtype=np.float32)

    # Initialize the MRIData object
    mri_data = MRIData(
        data=data,
        coords=coords,
        coords_cg=coords_cg,
        sdc=sdc,
        sdc_cg=sdc_cg,
        tmap=tmap
    )

    # Update parameters
    data_type = "SE"
    echo_times = np.array([[10, 20, 30]], dtype=np.float32)
    axes_labels = ["x", "y"]
    tau = 10.0
    mri_data.update_params(data_type, echo_times, axes_labels, "kspace", tau)

    # Access data and parameters
    print("K-space data:", mri_data.idata)
    print("Coordinates:", mri_data.coords)
    print("Sampling density compensation:", mri_data.sdc)
    print("Constant gradient coordinates:", mri_data.coords_cg)
    print("Constant gradient sampling density compensation:", mri_data.sdc_cg)
    print("Time map:", mri_data.tmap)
    print("Local data parameters:", mri_data.data_params)