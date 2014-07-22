'''
Contains Circuit and SubCircuit class definitions.  
'''

import numpy
import sympy
import numpy.linalg as la


#========================= CLASSES =============================

class SubCircuit():
  '''
  A SPICE subcircuit (.subckt) object. 
  '''
  def __init__(self, parent, name=None):
    '''
    Creates an empty SubCircuit.

    Arguments:
    parent -- the parent circuit or subcircuit.
    name   -- optional name.
    '''
    self.devices = {}
    self.nodes = 0
    self.name = name
    self.itr = 0
    self.converged = False
    self.simulator = None

  def stamp(self):
    '''
    Creates matrix stamps for the subcircuit network scope by stamping the
    devices together that belong to this subcircuit.
    '''
    self.jacobian[:,:] = 0.0
    self.bequiv[:] = 0.0
    for name, device in self.devices.items():
      for nodei in device.nodes:
        porti = device.node2port[nodei]
        self.bequiv[nodei] = self.bequiv[nodei] + device.bequiv[porti]
        for nodej in device.nodes:
          portj = device.node2port[nodej]
          self.jacobian[nodei, nodej] = self.jacobian[nodei, nodej] + device.jacobian[portj, porti]

  def setup(self, dt):
    '''
    Calls setup() on all of this subcircuit devices. Setup is called at the beginning
    of the simulation and allows the intial stamps to be applied.
    '''
    self.dt = dt
    for name, device in self.devices.items():
      device.setup(dt)
    self.across = numpy.zeros(self.nodes)
    self.across_last = numpy.zeros(self.nodes)
    self.across_history = numpy.zeros(self.nodes)
    self.jacobian = numpy.zeros((self.nodes, self.nodes))
    self.bequiv = numpy.zeros(self.nodes)
    self.jacobian2 = numpy.zeros((self.nodes-1, self.nodes-1))
    self.bequiv2 = numpy.zeros(self.nodes-1)
    self.stamp()

  def step(self, dt):
    '''
    Called at each timestep.
    Arguments:
    dt -- the timestep value (sec)
    '''
    self.across_last = numpy.copy(self.across)
    self.itr = 0
    self.converged = False
    while self.itr < self.simulator.maxitr and not self.converged:
      self.minor_step(dt)
      self.itr += 1

    self.across_history = numpy.copy(self.across) # save off history
    

  def minor_step(self, dt):
    '''
    Called before each Newton iteration.
    TODO: optimize for linear networks!!!
    '''
    
    #print self.across_last[2], self.across[2]
    for name, device in self.devices.items():
      device.minor_step(dt)
    self.stamp()
    self.jacobian2[:,:] = self.jacobian[1:, 1:] # chop off ground node
    self.bequiv2[:] = self.bequiv[1:]  # chop off ground node
    self.across[1:] = la.solve(self.jacobian2, self.bequiv2) # solve Ax = B

    # check convergance:
    self.converged = True
    for v0, v1 in zip(self.across_last, self.across):
      if abs(v1 - v0) > self.simulator.tol:
        self.converged = False
        break

    self.across_last = numpy.copy(self.across)


  def add_device(self, device):
    '''
    Adds a device to the subcircuit.
    Arguments:
    device -- the Device to add.
    '''
    device.subcircuit = self
    if not device.name in self.devices: # if the name is unique (not found in device dict)
      self.devices[device.name] = (device) # add the device with it's name as the key
      highest_node = max(device.nodes) # increment the subcircuit nodes as needed
      self.nodes = max(self.nodes, highest_node + 1)
    else:
      # TODO: throw duplicate device name exception (or auto-name?)
      # no, can't auto-name because user needs to use key to index
      pass


class Circuit(SubCircuit):
  '''
  A SPICE circuit object. There can only be one circuit in a network. The
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
  '''
  def __init__(self):
    '''
    Creates a circuit object.
    '''
    SubCircuit.__init__(self, parent=None)
    self.models = {}
    self.title1 = ''
    self.title2 = ''

  def add_model(self, model):
    '''
    Add a model (.model) definition to the Circuit.
    '''
    self.models[model.name] = model

  def from_spice(self, filepath):
    '''
    Imports the contents of a SPICE3-compliant circuit definition.
    Arguments:
    filepath -- the path of the file to import. 
    '''
    pass

  def to_spice(self, filepath):
    '''
    Exports this circuit definition to a SPICE3-compliant file.
    Arguments:
    filepath -- the path of the file to export to. 
    '''
    pass