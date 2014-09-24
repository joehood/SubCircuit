"""interfaces.py

Copyright 2014 Joe Hood

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import numpy as np


class DeviceFamilies(object):
    ELEMENTARY = 0
    INDEPENDANT_SOURCES = 1
    LINEAR_DEPENDANT_SOURCES = 2
    NONLINEAR_DEPENDANT_SOURCES = 3
    SEMICONDUCTORS = 4
    TRANSMISSION_LINES = 5


class Device(object):
    """A Device (circuit element) base object."""

    def __init__(self, nodes, family=None, **parameters):
        """Creates a device base.
        :param name: Mandatory name, unique within the parent subcircuit.
        :param nnodes: number of nodes for this device (including internal)
        :param kwargs: Additional keyword arguments stored in the params dict.
        :return: None
        """
        if isinstance(nodes, int):
            self.nodes = (nodes,)
        else:
            self.nodes = list(nodes)
        self.nnodes = len(self.nodes)
        self.family = family

        self.port2node = None
        self.name = None
        self.netlist = None
        self.parameters = parameters
        self.value = None

    def connect(self):
        """Virtual class. Must be implemented by derived class.
        :return: None.
        """
        raise NotImplementedError()

    def update(self):
        """
        TODO: doc
        :return:
        """
        pass

    def get_time(self):
        """Provides convenient access to the current simulation time.
        :return: The current time in seconds
        """
        return self.netlist.simulator.t

    def get_timestep(self):
        """Provides convenient access to the current simulation timestep.
        :return: The current timestep in seconds
        """
        return self.netlist.simulator.dt

    def get_node_index(self, name):
        return self.netlist.get_node_index(name)

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

    def start(self, dt):
        """Virtual method. Must be implemented by derived class.
        Called at the beginning of the simulation before the parent subcircuit's
        setup method is called and before the subcircuit's stamp is created.
        Should setup the initial device jacobian and bequiv stamps.
        """
        pass

    def step(self, dt, t):
        """Virtual method. Must be implemented by derived class.
        Called as each simulation timestep.
        """
        pass

    def post_step(self, dt, t):
        pass

    def minor_step(self, dt, t, k):
        """Virtual method. May be implemented by derived class.
        Called before each Newton interation. If device does not implement
        minor_step, self.step() will be called instead.
        """
        self.step(dt, t)
        pass

    def get_code_string(self):
        code_string = ""
        type_ = type(self).__name__
        nodes = str(self.nodes)
        value = str(self.value)

        plist = ""
        for pname, param in self.parameters.items():
            plist += ", {0}={1}".format(pname, param)

        if self.value:
            code_string = "{0}({1}, value={2}{3})".format(type_, nodes,
                                                          value, plist)
        else:
            code_string = "{0}({1}{3})".format(type_, nodes, value, plist)

        return code_string

    def __str__(self):
        s = "{0} {1}".format(self.name, self.nodes)
        return s

    def __repr__(self):
        return str(self)


class MNADevice(Device):
    """A Device (circuit element) base object."""

    def __init__(self, nodes, internals, **parameters):
        """Creates a device base.
        :param name: Mandatory name, unique within the parent subcircuit.
        :param nnodes: number of nodes for this device (including internal)
        :param kwargs: Additional keyword arguments stored in the params dict.
        :return: None
        """
        Device.__init__(self, nodes, **parameters)
        self.nodes = nodes
        self.nnodes = len(nodes) + internals
        self.jac = np.zeros((self.nnodes, self.nnodes))
        self.bequiv = np.zeros((self.nnodes, 1))

    def get_model(self, mname):
        """Provides convenient access to all models in the subcircuit
        :return: The model with key==mname, if it exists in the subcircuit.
        """
        if mname in self.netlist.models:
            return self.netlist.models[mname]
        else:
            return None

    def create_internal(self, name):
        return self.netlist.create_internal(name)


class SignalDevice(Device):
    def __init__(self, nodes, **parameters):
        Device.__init__(self, nodes, **parameters)


class Model(object):
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


class Subckt(object):
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


class CurrentSensor(object):
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


class Stimulus(object):
    """Represents an independant source simulus function (PULSE, SIN, etc). This class
    must be derived from and setup() and step() methods must be implemented.
    """

    def __init__(self):
        self.device = None

    def start(self, dt):
        """Virtual method. Must be implemented by derived class."""
        raise NotImplementedError

    def step(self, dt, t):
        """Virtual method. Must be implemented by derived class."""
        raise NotImplementedError


class Table(object):
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

    def output(self, input_):
        """Gets the corresponding output value for the provided input.
        :param input_: Input value
        :return: Output mapped to provided input
        """
        return self._interp_(input_)

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


class Plottable:
    def __init__(self):
        pass


class Voltage(Plottable):
    """Represents a plottable voltage value."""

    def __init__(self, node1=None, node2=0, device=None):
        """Creates a new plottable voltage object.
        Arguments:
        :param node1: The circuit node for the positive voltage
        :param node2: The circuit node for the negative voltage (0 by default)
        """
        Plottable.__init__(self)
        self.device = None
        self.node1 = None
        self.node2 = None
        if device:
            self.device = device
        elif node1:
            self.node1 = node1
            self.node2 = node2


class Current(Plottable):
    """Represents a plottable current value."""

    def __init__(self, vsource):
        """Creates a new plottable cuurent object.
        Arguments:
        vsource -- The name of the current-providing device.
        """
        Plottable.__init__(self)
        self.vsource = vsource