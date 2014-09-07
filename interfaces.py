"""interfaces.py"""

import numpy
import copy


class Device():
    """A Device (circuit element) base object."""

    def __init__(self, nnodes, **kwargs):
        """Creates a device base.
        :param name: Mandatory name, unique within the parent subcircuit.
        :param nnodes: number of nodes for this device (including internal)
        :param kwargs: Additional keyword arguments stored in the params dict.
        :return: None
        """
        self.nnodes = nnodes
        self.params = kwargs
        self.jac = numpy.zeros((nnodes, nnodes))
        self.bequiv = numpy.zeros((nnodes, 1))
        self.port2node = None
        self.netlist = None
        self.name = None
        self.nodes = None

    def map_nodes(self):
        """Virtual class. Must be implemented by derived class.
        :return: None.
        """
        raise NotImplementedError()

    def get_time(self):
        """Provides convenient access to the current simulation time.
        :return: The current time in seconds
        """
        return self.netlist.simulator.time

    def get_timestep(self):
        """Provides convenient access to the current simulation timestep.
        :return: The current timestep in seconds
        """
        return self.netlist.simulator.dt

    def get_model(self, mname):
        """Provides convenient access to all models in the subcircuit
        :return: The model with key==mname, if it exists in the subcircuit.
        """
        if mname in self.netlist.models:
            return self.netlist.models[mname]
        else:
            return None

    def get_node_index(self, name):
        return self.netlist.get_node_index(name)

    def create_internal(self, name):
        return self.netlist.create_internal(name)

    def get_across_history(self, port1=None, port2=None, device=None):
        """Gets the across value at the given ports for t-h (last timestep).
        If port2 is not provided, the across value returned is the across value
        of port1's node with respect to ground.
        :param port1: Device port 1 (positive for porposes of voltage metering)
        :param port2: Device port 2 (negetive for porposes of voltage metering)
        If port2 is not provide, voltage is given with respect to ground)
        :param device: Optional. If provided, returns the voltage across a
        2-port device with the given key if it exists within the subcircuit
        :return: Voltage in Volts
        """
        across = float('inf')
        if device:
            nodes = self.netlist.devices[device].nodes
            if len(nodes) > 1:
                across = self.netlist.across_history[0]
                across -= self.netlist.across_history[1]
        else:
            across = self.netlist.across_history[self.port2node[port1]]
            if port2:
                across -= self.netlist.across_history[self.port2node[port2]]
        return across

    def get_across(self, port1=None, port2=None, external_device=None):
        """Gets the across value for the current time and newton iteration
        If port2 is not provided, the across value returned is the across value
        of port1's node with respect to ground.
        :param port1: Device port 1 (positive for porposes of voltage metering)
        :param port2: Device port 2 (negetive for porposes of voltage metering)
        If port2 is not provide, voltage is given with respect to ground)
        :param external_device: Optional. If provided, returns the voltage
        across a 2-port device with the given key if it exists within the
        subcircuit
        :return: Voltage in Volts
        """
        if self.netlist.across_last is not None:
            across = float('inf')
            if external_device:
                nodes = self.netlist.devices[external_device].nodes
                assert len(nodes) > 1
                across = self.netlist.across_last[nodes[0]]
                across -= self.netlist.across_last[nodes[1]]
            else:
                a = 5
                across = self.netlist.across_last[self.port2node[port1]]
                if port2:
                    across -= self.netlist.across_last[self.port2node[port2]]
            return across
        else:
            # TODO: what is return value when across vector not initialized?
            return 0.0

    def setup(self, dt):
        """Virtual method. Must be implemented by derived class.
        Called at the beginning of the simulation before the parent subcircuit's
        setup method is called and before the subcircuit's stamp is created.
        Should setup the initial device jacobian and bequiv stamps.
        """
        pass

    def step(self, t, dt):
        """Virtual method. Must be implemented by derived class.
        Called as each simulation timestep.
        """
        pass

    def minor_step(self, k, t, dt):
        """Virtual method. May be implemented by derived class.
        Called before each Newton interation. If device does not implement
        minor_step, self.step() will be called instead.
        """
        self.step(t, dt)
        pass

    def clone(self):
        """Produce a clone of this device instance.
        :return: Cloned device instance
        """
        other = Device(self.nnodes, self.params)
        other.nodes = self.nodes
        other.subckt = self.subckt  # parent subcircuit
        other.name = self.name
        return other


class Model():
    """Base model (.model) object."""

    def __init__(self, name, **kwargs):
        """Creates a base Model.
        Arguments:
        name    -- Mandatory model name (most be unique within the circuit).
        circuit -- Parent circuit
        kwargs  -- additional keyword arguments. Stored in params dict.
        """
        self.name = name
        self.params = kwargs


class Subckt():
    """A SPICE subcircuit definition (.subckt)"""

    def __init__(self, ports, **parameters):
        """Creates a new subcircuit definition.
        :param name: Name of subcircuit. Must be unique within parent subckt
        :param ports: External ports in the same order as subcircuit instances
        :param parameters: Subcircuit parameters.
        :return: A new subcircuit.
        """
        self.ports = ports
        self.parameters = parameters
        self.netlist = None
        self.devices = {}
        self.nnodes = 0
        self.parent = None
        self.name = None

    def map_nodes(self):
        # TODO: fix
        self.nnodes = 2  # TODO: determine how many nodes here.

    def device(self, name, device):
        """Add a device to the subcircuit
        :param name:
        :param device:
        :return: True if successful. False if failed.
        """
        if not name in self.devices:
            self.devices[name] = device
            device.name = name
            device.subckt = self
            return True
        else:
            return False


class CurrentSensor():
    """Interface for current sensor device.
    Should derive from this class and implement get_current_node if this
    device has the ability to provide branch current information via an internal
    branch-current node.
    """

    def __init__(self):
        pass

    def get_current_node(self):
        """Virtual method. Must be implemented by derived class.
        Must return a 2-tuple with (node, scale) where node is the system node
        index of the current node, and scale is a multiplier (ie. 1 or -1)"""
        pass


class Stimulus():
    """Represents an independant source simulus function (PULSE, SIN, etc). This class
    must be derived from and setup() and step() methods must be implemented.
    """

    def __init__(self):
        self.device = None

    def setup(self, dt):
        """Virtual method. Must be implemented by derived class."""
        raise NotImplementedError

    def step(self, t, dt):
        """Virtual method. Must be implemented by derived class."""
        raise NotImplementedError


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


class PySpyceError(Exception):
    def __init__(self, msg):
        """Creates a new PySpyceError
        :param msg: Error message
        """
        Exception.__init__(self, "PySpyce Error: {0}".format(msg))
