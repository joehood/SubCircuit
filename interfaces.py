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

    def __init__(self, name, ports, **kwargs):
        """
        Creates a base Device.
        Aruguments:
        :param name: Mandatory name. Must be unique within the parent's subcircuit.
        :param ports: A sequence of the port indeces.
        :param subcircuit: The parent subcircuit.
        :param kwargs: Additional keyword arguments stored in the params dict.
        """
        self.name = name
        self.jac = numpy.zeros((ports, ports))
        self.bequiv = numpy.zeros((ports, 1))
        self.params = kwargs
        self.device = None
        self.subcircuit = None
        self.nodes = 0

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

    def get_across(self, port1=None, port2=None, device=None):
        """Get the across value between the nodes to which the given ports are attached.
        If port2 is not provided, the across value returned is the across value of port1's
        node with respect to ground.
        """
        across = float('inf')
        if device:
            nodes = self.subcircuit.devices[device].nodes
            if len(nodes) > 1:
                across = self.subcircuit.across_last[0]
                across -= self.subcircuit.across_last[1]
        else:
            across = self.subcircuit.across_last[self.nodes[port1]]
            if port2:
                across -= self.subcircuit.across_last[self.nodes[port2]]
        return across

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

    def get_current_node(self):
        """Virtual method. Must be implemented by derived class."""
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
