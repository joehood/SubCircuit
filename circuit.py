"""
Contains Circuit and SubCircuit class definitions.
"""

import numpy
import numpy.linalg as la


# ========================= CLASSES =============================

class SubCircuit():
    """A SPICE subcircuit (.subckt) object. """

    def __init__(self, parent, name=None):
        """Creates an empty SubCircuit.

        Arguments:
        parent -- the parent circuit or subcircuit.
        name   -- optional name.
        """
        self.nodes = 0
        self.across = None
        self.across_last = None
        self.across_history = None
        self.jacobian = None
        self.bequiv = None
        self.jacobian2 = None
        self.bequiv2 = None
        self.across_last = None
        self.across_history = None
        self.across_last = None
        self.devices = {}
        self.name = name
        self.converged = False
        self.simulator = None
        self.dt = 0.0

    def stamp(self):
        """Creates matrix stamps for the subcircuit network scope by stamping the
        devices together that belong to this subcircuit.
        """
        self.jacobian[:, :] = 0.0
        self.bequiv[:] = 0.0
        for name, device in self.devices.items():
            for nodei in device.nodes:
                porti = device.node2port[nodei]
                self.bequiv[nodei] = self.bequiv[nodei] + device.bequiv[porti]
                for nodej in device.nodes:
                    portj = device.node2port[nodej]
                    self.jacobian[nodei, nodej] = self.jacobian[nodei, nodej] + device.jacobian[portj, porti]

    def setup(self, dt):
        """Calls setup() on all of this subcircuit devices. Setup is called at the beginning
        of the simulation and allows the intial stamps to be applied.
        """
        # determine node size:
        self.dt = dt
        for name, device in self.devices.items():
            device.setup(dt)
            highest_node = max(device.nodes)  # increment the subcircuit nodes as needed
            self.nodes = max(self.nodes, highest_node + 1)

        self.across = numpy.zeros(self.nodes)
        self.across_last = numpy.zeros(self.nodes)
        self.across_history = numpy.zeros(self.nodes)
        self.jacobian = numpy.zeros((self.nodes, self.nodes))
        self.bequiv = numpy.zeros(self.nodes)
        self.jacobian2 = numpy.zeros((self.nodes - 1, self.nodes - 1))
        self.bequiv2 = numpy.zeros(self.nodes - 1)
        self.stamp()

    def step(self, t, dt):
        """
        Steps the circuit:
        :param t: the current time.
        :param dt: the current timestep
        :return: None
        """
        k = 0
        self.converged = False
        while k < self.simulator.maxitr and not self.converged:
            self.minor_step(k, t, dt)
            k += 1

        self.across_last = numpy.copy(self.across)  # init newton state
        self.across_history = numpy.copy(self.across)  # save off history


    def minor_step(self, k, t, dt):
        """Called at each Newton iteration."""

        # minor step all devices in this subcircuit:
        for name, device in self.devices.items():
            device.minor_step(k, t, dt)

        # re-stamp the subcircuit matrices with the updated information:
        self.stamp()

        # get submatrices that don't include the ground node:
        self.jacobian2[:, :] = self.jacobian[1:, 1:]
        self.bequiv2[:] = self.bequiv[1:]

        # solve across vector from linear system: jacobian * across = b-equivalent (Ax = B):
        self.across[1:] = la.solve(self.jacobian2, self.bequiv2)

        # check convergence criteria:
        self.converged = True
        for v0, v1 in zip(self.across_last, self.across):
            if abs(v1 - v0) > self.simulator.tol:
                self.converged = False
                break

        # save off across vector state for this iteration:
        self.across_last = numpy.copy(self.across)


    def add_device(self, device):
        """Adds a device to the subcircuit.
        Arguments:
        device -- the Device to add.
        """
        device.subcircuit = self
        if not device.name in self.devices:  # if the name is unique (not found in device dict)
            self.devices[device.name] = device  # add the device with it's name as the key

        else:
            # TODO: throw duplicate device name exception (or auto-name?)
            # no, can't auto-name because user needs to use key to index
            pass


class Circuit(SubCircuit):
    """A SPICE circuit object. There can only be one circuit in a network. The
    circuit is a special type of SubCircuit and Circuit derives from the base
    class SubCircuit. The network circuit differs from the other SubCircuits in
    the following ways:

    1. The Circuit is the root network's SubCircuit tree, and therefore it's parent
        is None.
    2. The Circuit has two title fields (title1 and title2) to emulate the title
        fields present in typical SPICE netlist or .cir files.
    3. The Circuit contains device models (.model definitions) that may be used by
        devices contained within itself or within it's children SubCircuits
    4. A Circuit has from_spice and to_spice functions for imorting/exporting
        SPICE3-compliant netlists.
    """

    def __init__(self):
        """Creates a circuit object."""
        SubCircuit.__init__(self, parent=None)
        self.models = {}
        self.title = ''

    def add_model(self, model):
        """Add a model (.model) definition to the Circuit."""
        self.models[model.name] = model

    def from_spice(self, filepath):
        """Imports the contents of a SPICE3-compliant circuit definition.
        Arguments:
        filepath -- the path of the file to import.
        """
        pass

    def to_spice(self, filepath):
        """Exports this circuit definition to a SPICE3-compliant file.
        Arguments:
        filepath -- the path of the file to export to.
        """
        pass