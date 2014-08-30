"""Contains base class definitions for spyce Models and Devices."""

from circuit import *


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


class Device():
    """A Device (circuit element) base object."""

    def __init__(self, numnodes, **kwargs):
        """
        Creates a base Device.
        Aruguments:
        :param name: Mandatory name. Must be unique within the parent's subcircuit.
        :param ports: A sequence of the port indeces.
        :param subcircuit: The parent subcircuit.
        :param kwargs: Additional keyword arguments stored in the params dict.
        """
        self.params = kwargs
        self.jac = numpy.zeros((numnodes, numnodes))
        self.bequiv = numpy.zeros((numnodes, 1))
        self.nodes = None
        self.subcircuit = None
        self.name = None

    def map_nodes(self):
        raise NotImplementedError()

    def get_time(self):
        return self.subcircuit.simulator.time

    def get_timestep(self):
        return self.subcircuit.simulator.dt

    def get_model(self, mname):
        if mname in self.subcircuit.models:
            return self.subcircuit.models[mname]
        else:
            return None

    def get_across_history(self, port1=None, port2=None, device=None):
        """Get the across value between the nodes to which the given ports are attached.
        If port2 is not provided, the across value returned is the across value of port1's
        node with respect to ground.
        """
        across = float('inf')
        if device:
            nodes = self.subcircuit.devices[device].nodes
            if len(nodes) > 1:
                across = self.subcircuit.across_history[0]
                across -= self.subcircuit.across_history[1]
        else:
            across = self.subcircuit.across_history[self.nodes[port1]]
            if port2:
                across -= self.subcircuit.across_history[self.nodes[port2]]
        return across

    def get_across(self, port1=None, port2=None, external_device=None):
        """Get the across value between the nodes to which the given ports are attached.
        If port2 is not provided, the across value returned is the across value of port1's
        node with respect to ground.
        """
        if self.subcircuit.across_last is not None:
            across = float('inf')
            if external_device:
                nodes = self.subcircuit.devices[external_device].nodes
                assert len(nodes) > 1
                across = self.subcircuit.across_last[nodes[0]]
                across -= self.subcircuit.across_last[nodes[1]]
            else:
                a = 5
                across = self.subcircuit.across_last[self.nodes[port1]]
                if port2:
                    across -= self.subcircuit.across_last[self.nodes[port2]]
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
        Called before each Newton interation. If device does not implement minor_step, self
        """
        self.step(t, dt)
        pass


class CurrentSensor():
    """Should derive from this class and implement get_current_node if this device has
    the ability to provide branch current information via an internal (gyrator) node.
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


class NodePortMap(dict):
    pass
    # """Speciailized dictionary that maps efficiently both ways.
    # This can use either the keys or the values as keys. This is only appropriate
    # for one-to-one mappings, which is the case as long as this is only used
    # internally for a device. A device cannot contribute multiple ports to one
    # node.
    # """
    # def __setitem__(self, key, value):
    #     if key in self:
    #         del self[key]
    #     if value in self:
    #         del self[value]
    #     dict.__setitem__(self, key, value)
    #     dict.__setitem__(self, value, key)
    #
    # def __delitem__(self, key):
    #     dict.__delitem__(self, self[key])
    #     dict.__delitem__(self, key)
    #
    # def __len__(self):
    #     """Returns the number of connections"""
    #     return dict.__len__(self) // 2