'''
Contains base class definitions for spyce Models and Devices.
'''

import numpy
from circuit import *

class Model():
  '''
  Base model (.model) object.
  '''
  def __init__(self, name, circuit=None, **kwargs):
    '''
    Creates a base Model.
    Arguments:
    name    -- Mandatory model name (most be unique within the circuit).
    circuit -- Parent circuit
    kwargs  -- additional keyword arguments. Stored in params dict.
    '''
    self.name = name
    self.circuit = circuit
    self.params = kwargs


class Device():
  '''
  A Device (circuit element) base object.
  '''
  def __init__(self, name, ports, **kwargs):
    '''
    Creates a base Device.
    Aruguments:
    name --        Mandatory name. Must be unique within the parent subcircuit.
    ports --       A sequence of the port indeces.
    subcircuit --  The parent subcircuit.
    kwargs --      Additional keyword arguments stored in the params dict. 
    '''
    self.name = name
    self.jacobian = numpy.zeros((ports, ports))
    self.bequiv = numpy.zeros((ports, 1))
    self.params = kwargs

  def get_time(self):
    return self.subcircuit.simulator.time

  def setup(self, dt):
    '''Virtual method. Must be implemented by derived class.
    Called at the beginning of the simulation before the parent subcircuit's
    setup method is called and before the subcircuit's stamp is created.
    Should setup the initial device jacobian and bequiv stamps.
    '''
    pass

  def step(self, dt):
    '''Virtual method. Must be implemented by derived class.
    Called as each simulation timestep. 
    '''
    pass

  def minor_step(self, dt):
    '''Virtual method. Must be implemented by derived class.
    Called before each Newton interation. Only called if the network is non-linear.
    '''
    self.step(dt)
    pass

class CurrentSensor():
  '''Should derive from this class and implement get_current_node if this device has
  the ability to provide branch current information via an internal (gyrator) node.
  '''
  def get_current_node(self):
    '''Virtual method. Must be implemented by derived class.'''
    pass


class Stimulus():
  '''
  Represents an independance source simulus function (PULSE, SIN, etc). This class
  must be derived from and setup() and step() methods must be implemented.
  '''
  def setup(self, source):
    '''Virtual method. Must be implemented by derived class.'''
    pass
  def step(self, source, dt):
    '''Virtual method. Must be implemented by derived class.'''
    pass