"""Contains Circuit and SubCircuit class definitions."""

from __future__ import print_function
from copy import deepcopy as clone

from scipy.sparse import csc_matrix as smatrix
import numpy as np
import numpy.linalg as la

from devices import *
import simulator as sim


class Netlist():

    """A SPICE netlist object."""

    def __init__(self, title=''):
        """Creates a netlist object."""

        # title:
        self.title = title
        self.devices = {}
        self.models = {}
        self.subckts = {}  # subcircuit definitions

        # node management:
        self.nodes = {'ground': 0, 'gnd': 0, 0: 0}  # pre-load with ground node
        self.nodenum = 1
        self.internalnum = 0

        # network matrices:
        self.across = None  # across at current time and iteration
        self.across_last = None  # across at last iteration
        self.across_history = None  # across at end of last time step
        self.jac = None
        self.sjac = None  # sparce jacobian for fast factorization
        self.bequiv = None

        # simulator:
        self.simulator = sim.Simulator(self)
        self.converged = False
        self.dt = 0.0

    def flatten(self):

        """Flattens all the subcircuits recursively to the main subcircuit.
        :return: None
        """

        # now loop through and grab all the subcircuit instances and remove from
        # device list:

        for x_name, x_device in self.devices.items():

            if isinstance(x_device, X):  # if subckt instance device:

                subckt_name = x_device.subckt

                if subckt_name in self.subckts:  # if subckt def found:

                    subckt = self.subckts[subckt_name]

                    # loop through the subckt devices, clone them for the
                    # subckt instance, and mangle the names to prevent
                    # collisions:

                    for sub_name, sub_device in subckt.devices.items():
                        mangled_name = "{0}_{1}".format(x_name, sub_name)
                        new_device = clone(sub_device)

                        # replace subckt instance device node names with
                        # external node names & mangle the internal node names:

                        for i, node in enumerate(new_device.nodes):
                            if node == 0 or node == 'ground' or node == 'gnd':
                                new_device.nodes[i] = 0
                            elif node in x_device.port2node:
                                new_device.nodes[i] = x_device.port2node[node]
                            else:
                                mangled_port = "{0}_{1}".format(x_name, node)
                                new_device.nodes[i] = mangled_port

                        # add device to top level:
                        self.device(mangled_name, new_device)

                    # delete the X device (which has now been replaced with
                    # actual device instances and is no longer needed):

                    del self.devices[x_name]

                else:  # if subckt definition not found:

                    msg = "Subcircuit {0} not defined for device {1}."
                    msg.format(x_device.subckt, x_name)
                    raise PySpyceError(msg)

    def setup(self, dt):
        """Calls setup() on all of this subcircuit devices.
        Setup is called at the beginning of the simulation and allows the
        intial stamps to be applied.
        """
        # dimension matrices:
        n = self.nodenum
        self.across = np.zeros(n)
        self.across_last = np.zeros(n)
        self.across_history = np.zeros(n)
        self.jac = np.zeros((n, n))
        self.bequiv = np.zeros(n)
        self.sjac = smatrix((n-1, n-1))

        # setup devices:
        for device in self.devices.values():
            device.start(dt)

        # stamp the ciruit:
        self.stamp()

    def stamp(self):
        """Stamps the main subcircuit devices.
        """
        self.jac[:, :] = 0.0
        self.bequiv[:] = 0.0
        for device in self.devices.values():
            if isinstance(device, MNADevice):
                for pi, ni in device.port2node.items():
                    self.bequiv[ni] += device.bequiv[pi]
                    for pj, nj in device.port2node.items():
                        self.jac[ni, nj] += device.jac[pi, pj]

    def step(self, dt, t):
        """Steps the circuit to the next timestep.
        :param t: the current time.
        :param dt: the current timestep
        :return: True is step is successful (no errors)
        """
        success = True

        k = 0
        self.converged = False
        while k < self.simulator.maxitr and not self.converged:
            success = self.minor_step(dt, t, k)
            if not success:
                break
            k += 1

        self.across_last = np.copy(self.across) # update netwon state at k=0
        self.across_history = np.copy(self.across)  # save off across history

        for device in self.devices.values():
            device.post_step(dt, t)

        # self.print_matrices()

        return success, k

    def print_matrices(self):
        s = "\nt = {0}\n".format(self.simulator.get_current_time())
        print(s)
        row = " " * 13
        names = [0]
        for i in range(1, self.nodenum):
            node_name = ""
            for name, index in self.nodes.items():
                if index == i:
                    names.append(name)
                    node_name = name
                    break
            s = "{0:>12}  ".format(node_name)
            row += s
        print(row)
        print(" " * 14 + "." + (len(row) - 9) * '-' + ".")

        for i in range(1, self.nodenum):
            row = "{0:>12}  |".format(names[i])
            for j in range(1, self.nodenum):
                s = "{0:12.2g}  "
                row += s.format(self.jac[i, j].astype(float))
            s = "    |     {0:12.2g}"
            row += s.format(self.across[i].astype(float))
            s = "    |     {0:12.2g}"
            row += s.format(self.bequiv[i].astype(float))
            print(row)
        print(" " * 14 + "'" + (len(row) - 55) * '-' + "'")

    def minor_step(self, dt, t, k):
        """Called at each Newton iteration until convergance or itr > maxitr.
        :param k: Current newton iteration index
        :param t: Current simulation time
        :param dt: Current simulation timestep
        :return: True is step is successful (no errors)
        """
        success = True

        # minor step all devices in this subcircuit:
        for device in self.devices.values():
            device.minor_step(dt, t, k)

        # re-stamp the subcircuit matrices with the updated information:
        self.stamp()

        # solve across vector from linear system:
        # jacobian * across = b-equivalent (Ax = B):
        try:
            #lu = sla.splu(self.sjac)
            #self.across[1:] = lu.solve(self.bequiv[1:])
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
        self.across_last = np.copy(self.across)

        return success

    def get_node_index(self, key):
        if not key in self.nodes:
            self.nodenum += 1
            self.nodes[key] = self.nodenum - 1
        return self.nodes[key]

    def create_internal(self, name):
        self.nodenum += 1
        self.internalnum += 1
        if not name in self.nodes:
            self.nodes[name] = self.nodenum - 1
        else:
            s = "Internal node name {0} is not unique."
            s.format(name)
            raise PySpyceError(s)
        return self.nodenum - 1

    def device(self, name, device):
        """Add a device to the netlist
        :param name:
        :param device:
        :return: True if successful. False if failed.
        """
        if not name in self.devices:
            self.devices[name] = device
            device.name = name
            device.netlist = self
            device.connect()
            return True
        else:
            return False

    def model(self, name, model):
        """Add a model (.model) definition to the Circuit.
        :param model: Model definition to add.
        :return: None
        """
        self.models[name] = model

    def subckt(self, name, subckt):
        """Adds subcircuit (.subckt) definition to the circuit.
        Also creates a subcircuit generator object
        :param subckt:
        :return: Subcircuit insatnce generator
        """
        self.subckts[name] = subckt
        subckt.name = name
        subckt.netlist = self
        return subckt

    def trans(self, tstep, tstop, tstart=None, tmax=None, uic=False):
        """
        Run transient simulation.
        :param tstep: Time step in seconds
        :param tstop: Simulation stop time in seconds
        :param tstart: TODO
        :param tmax: TODO
        :param uic: Flag for use initial conditions
        :return: None
        """
        self.flatten()
        self.simulator.trans(tstep, tstop, tstart, tmax, uic)

    def plot(self, *variables, **kwargs):
        """ Plot selected circuit variables
        :param variables: Plottables. Example: Voltage(1,2), Current('VSENSE')
        :param kwargs: TODO
        :return: None
        """
        return self.simulator.plot(*variables, **kwargs)

    def simulation_hook(self, dt, t):
        pass


class PySpyceError(Exception):
    def __init__(self, msg):
        """Creates a new PySpyceError
        :param msg: Error message
        """
        Exception.__init__(self, "PySpyce Error: {0}".format(msg))