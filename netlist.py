"""Contains Circuit and SubCircuit class definitions."""

from __future__ import print_function
from interfaces import *
from devices import *
import simulator
import numpy
import numpy.linalg as la


class Netlist():

    """A SPICE netlist object."""

    def __init__(self, title=''):
        """Creates a netlist object."""

        # title:
        self.title = title

        self.models = {}
        self.subckts = {}  # subcircuit definitions
        self.main_subckt = Subckt("main")  # main subcircuit definition
        self.main_subckt.netlist = self  # add circuit reference to main subckt
        self.subckt_instances = None
        self.devices = None

        # node management:
        self.nodes = {0: 0, 'ground': 0, 'gnd': 0}  # pre-load with ground node
        self.nodenum = 1
        self.internalnum = 0

        # network matrices:
        self.across = None  # across at current time and iteration
        self.across_last = None  # across at last iteration
        self.across_history = None  # across at end of last time step
        self.jac = None
        self.bequiv = None

        # simulator:
        self.simulator = simulator.Simulator(self)
        self.converged = False
        self.dt = 0.0

    def flatten(self):
        """Flattens all the subcircuits recursively to the main subcircuit.
        :return: None
        """
        # first, load top-level devices from the main subcircuit:
        self.devices = self.main_subckt.devices

        # now loop through and grab all the subcircuit instances and remove from
        # device list:
        self.subckt_instances = {}
        for name, device in self.devices.items():
            if isinstance(device, X):
                self.subckt_instances[name] = device.subckt
                del self.devices[name]

        # now add the devices from the subcircuits to the netlist, setting them
        # up with unique (mangled) device names and internal node names:
        for subckt_name, subckt_instance in self.subckt_instances.items():
            for device_name, device in subckt_instance.devices.items():
                mangled_name = "{0}_{1}".format(subckt_name, device_name)
                self.devices[mangled_name] = device
                device.name = mangled_name


    def stamp(self):
        """Stamps the main subcircuit devices.
        """
        self.jac[:, :] = 0.0
        self.bequiv[:] = 0.0
        for device in self.main_subckt.devices.values():
            for pi, ni in device.nodes.items():
                self.bequiv[ni] += device.bequiv[pi]
                for pj, nj in device.nodes.items():
                    self.jac[ni, nj] += device.jac[pi, pj]

    def setup(self, dt):
        """Calls setup() on all of this subcircuit devices.
        Setup is called at the beginning of the simulation and allows the
        intial stamps to be applied.
        """
        # dimension matrices:
        self.across = numpy.zeros(self.nodenum)
        self.across_last = numpy.zeros(self.nodenum)
        self.across_history = numpy.zeros(self.nodenum)
        self.jac = numpy.zeros((self.nodenum, self.nodenum))
        self.bequiv = numpy.zeros(self.nodenum)

        # setup devices:
        for device in self.main_subckt.devices.values():
            device.setup(dt)

        # stamp the ciruit:
        self.stamp()

    def step(self, t, dt):
        """Steps the circuit to the next timestep.
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

        self.print_matrices()

        return success

    def print_matrices(self):
        mstr = ""
        for i in range(self.nodenum-1):
            row = ""
            for j in range(self.nodenum-1):
                s = "{0:8.2g}  "
                row += s.format(self.jac[i+1, j+1].astype(float))
            s = "    |     {0:8.2g}"
            row += s.format(self.across[i+1].astype(float))
            s = "    |     {0:8.2g}"
            mstr += row + s.format(self.bequiv[i+1].astype(float)) + '\n'
        print(mstr)

    def minor_step(self, k, t, dt):
        """Called at each Newton iteration until convergance or itr > maxitr.
        :param k: Current newton iteration index
        :param t: Current simulation time
        :param dt: Current simulation timestep
        :return: True is step is successful (no errors)
        """
        success = True

        # minor step all devices in this subcircuit:
        for device in self.main_subckt.devices.values():
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

    def get_node_index(self, key):
        if not key in self.nodes:
            self.nodenum += 1
            self.nodes[key] = self.nodenum - 1
        return self.nodes[key]

    def create_internal(self):
        self.nodenum += 1
        self.internalnum += 1
        key = 'internal{0}'.format(self.internalnum - 1)
        self.nodes[key] = self.nodenum - 1
        return self.nodenum - 1

    def device(self, name, device):
        """Add a device to the main subcircuit.
        :param name: Name of device
        :param device: Device instance
        :return:
        """
        return self.main_subckt.device(name, device)

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
        return self.simulator.plot(self, *variables, **kwargs)


class Table():
    """Generic lookup table for transfer functions of dependant sources."""

    def __init__(self, *pairs):
        """Creates a new table instance.
        :param device: Parent device.
        :param pairs: Sequences of length 2 mapping dependant source inputs to
        outputs.
        :return: None
        """
        self.xp = []
        self.yp = []
        for x, y in pairs:
            self.xp.append(x)
            self.yp.append(y)
        self.cursor = 0  # this is to save the interp cursor state for speed

    def output(self, _input):
        """Gets the corresponding output value for the provided input.
        :param _input: Input value
        :return: Output mapped to provided input
        """
        return self._interp_(_input)

    def _interp_(self, x):
        if x <= self.xp[0]:
            return self.yp[0]
        elif x >= self.xp[-1]:
            return self.yp[-1]
        else:
            i = self.cursor
            while x > self.xp[i] and i < (len(self.xp) - 1):
                i += 1
            self.cursor = i
            x0, y0 = self.xp[i - 1], self.yp[i - 1]
            x1, y1 = self.xp[i], self.yp[i]
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)

