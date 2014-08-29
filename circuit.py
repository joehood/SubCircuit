"""Contains Circuit and SubCircuit class definitions."""

from __future__ import print_function
import numpy
import numpy.linalg as la


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
        self.jac = None
        self.bequiv = None
        self.across_last = None
        self.across_history = None
        self.across_last = None
        self.devices = {}
        self.name = name
        self.converged = False
        self.simulator = None
        self.dt = 0.0

    def stamp(self):
        """Creates matrix stamps for the subcircuit network scope by stamping
        the devices together that belong to this subcircuit.
        """
        self.jac[:, :] = 0.0
        self.bequiv[:] = 0.0
        for name, device in self.devices.items():
            for ni in device.nodes:
                pi = device.node2port[ni]
                self.bequiv[ni] += device.bequiv[pi]
                for nj in device.nodes:
                    pj = device.node2port[nj]
                    self.jac[ni, nj] += device.jac[pi, pj]

    def setup(self, dt):
        """Calls setup() on all of this subcircuit devices.
        Setup is called at the beginning of the simulation and allows the
        intial stamps to be applied.
        """
        # determine node size:
        self.dt = dt
        for name, device in self.devices.items():
            device.setup(dt)
            highest_node = max(device.nodes)  # increment the subcircuit nodes
            self.nodes = max(self.nodes, highest_node + 1)

        # dimension matrices:
        self.across = numpy.zeros(self.nodes)
        self.across_last = numpy.zeros(self.nodes)
        self.across_history = numpy.zeros(self.nodes)
        self.jac = numpy.zeros((self.nodes, self.nodes))
        self.bequiv = numpy.zeros(self.nodes)

        # stamp the ciruit:
        self.stamp()

    def step(self, t, dt):

        """
        Steps the circuit:
        :param t: the current time.
        :param dt: the current timestep
        :return: True is step is successful (no errors)
        """

        success = True

        k = 0
        self.converged = False
        while k < self.simulator.maxitr and not self.converged:
            success = self.minor_step(k, t, dt)
            if not success:
                break
            k += 1

        self.across_last = numpy.copy(self.across)  # update netwon state at k=0
        self.across_history = numpy.copy(self.across)  # save off across history

        # FOR DEBUGGING: code for dumping matrices:
        string = ""
        for i in range(self.nodes-1):
            row = ""
            for j in range(self.nodes-1):
                row += "{0:8.2g}  ".format(self.jac[i+1, j+1].astype(float))
            row += "    |     {0:8.2g}".format(self.across[i+1].astype(float))
            string += row + "    |     {0:8.2g}".format(self.bequiv[i+1].astype(float)) + '\n'
        print(string)

        return success

    def minor_step(self, k, t, dt):

        """Called at each Newton iteration.
        :param k: Current newton iteration index
        :param t: Current simulation time
        :param dt: Current simulation timestep
        :return: True is step is successful (no errors)
        """

        success = True

        # minor step all devices in this subcircuit:
        for name, device in self.devices.items():
            device.minor_step(k, t, dt)

        # re-stamp the subcircuit matrices with the updated information:
        self.stamp()

        # solve across vector from linear system:
        # jacobian * across = b-equivalent (Ax = B):
        try:
            self.across[1:] = la.solve(self.jac[1:, 1:], self.bequiv[1:])
        except la.LinAlgError as laerr:
            print("Linear algebra error occured while attempting to solve "
                  "circuit. Circuit not solved. Error details: ", laerr.message)
            success = False

        # check convergence criteria:
        if success:
            self.converged = True
            for v0, v1 in zip(self.across_last, self.across):
                if abs(v1 - v0) > self.simulator.tol:
                    self.converged = False
                    break

        # save off across vector state for this iteration:
        self.across_last = numpy.copy(self.across)

        return success

    def add_device(self, device):
        """Adds a device to the subcircuit.
        Arguments:
        device -- the Device to add.
        """
        device.subcircuit = self
        if not device.name in self.devices:  # if the name is unique
            self.devices[device.name] = device  # add the device, name is key

        else:
            # TODO: throw duplicate device name exception (or auto-name?)
            # no, can't auto-name because user needs to use key to index
            # ...or does he? maybe go with straight OOP method and require
            # user to use object reference and not names as keys??
            pass

    def add_devices(self, *devices):
        """Add multiple devices to subcircuit.
        :param devices: Devices to add.
        :return: None
        """
        for device in devices:
            self.add_device(device)


class Circuit(SubCircuit):

    """A SPICE circuit object. There can only be one circuit in a network. The
    circuit is a special type of SubCircuit and Circuit derives from the base
    class SubCircuit. The network circuit differs from the other SubCircuits in
    the following ways:

    1. The Circuit is the root network's SubCircuit tree, and therefore it's
       parent is None.
    2. The Circuit has two title fields (title1 and title2) to emulate the title
       fields present in typical SPICE netlist or .cir files.
    3. The Circuit contains device models (.model definitions) that may be used
       by devices contained within itself or within it's children SubCircuits
    """

    def __init__(self):
        """Creates a circuit object."""
        SubCircuit.__init__(self, parent=None)
        self.models = {}
        self.title = ''

    def add_model(self, model):
        """Add a model (.model) definition to the Circuit."""
        self.models[model.name] = model

