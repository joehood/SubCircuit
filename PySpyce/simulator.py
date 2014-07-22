'''
Contains the functions for analysis and simulation of a provided SPICE network.
'''

import numpy
import sympy
import matplotlib.pyplot as plt

from circuit import *
from devices import *
from interfaces import *


class Voltage():
  '''
  Represents a plottable voltage value.
  '''
  def __init__(self, node1, node2=0):
    '''
    Creates a new plottable voltage object.
    Arguments:
    node1 -- The circuit node for the positive voltage
    node2 -- The optional circuit node for the negative voltage (0 [ground] by default)
    '''
    self.node1 = node1
    self.node2 = node2


class Current():
  '''
  Represents a plottable current value.
  '''
  def __init__(self, vsource):
    '''
    Creates a new plottable cuurent object.
    Arguments:
    vsource -- The name of the current-providing device.
    '''
    self.vsource = vsource
  

class Simulator():
  '''
  Represents a SPICE simulator and provides the functions for SPICE simulation
  and analysis.
  '''
  def __init__(self, circuit, maxitr=100, tol=0.001):
    '''
    Creates a new Simulator instance for the provided circuit.
    Arguments:
    circuit -- The circuit to simulate.
    '''
    self.circuit = circuit
    self.circuit.simulator = self
    self.time = 0.0
    self.maxitr = maxitr
    self.tol = tol

  def ac(self):
    '''
    Not implemented.
    '''
    pass
  
  def dc(self):
    '''
    Not implemented.
    '''
    pass

  def distro(self):
    '''
    Not implemented.
    '''
    pass

  def noise(self):
    '''
    Not implemented.
    '''
    pass

  def op(self):
    '''
    Not implemented.
    '''
    pass

  def pz(self):
    '''
    Not implemented.
    '''
    pass

  def sens(self):
    '''
    Not implemented.
    '''
    pass

  def tf(self):
    '''
    Not implemented.
    '''
    pass

  def trans(self, tstep, tstop, start=None, stop=None, uic=False):
    '''.TRAN: Transient Analysis
    General form:
    .TRAN TSTEP TSTOP <TSTART; <TMAX;>>
    Examples:
    .TRAN 1NS 100NS
    .TRAN 1NS 1000NS 500NS
    .TRAN 10NS 1US
    TSTEP is the printing or plotting increment for line-printer output. For
    use with the post-processor, TSTEP is the suggested computing increment. 
    TSTOP is the final time, and TSTART is the initial time. If TSTART is
    omitted, it is assumed to be zero. The transient analysis always begins
    at time zero. In the interval &ltzero;, TSTART>, the circuit is analyzed
    (to reach a steady state), but no outputs are stored. In the interval
    &ltTSTART;, TSTOP>, the circuit is analyzed and outputs are stored. TMAX
    is the maximum stepsize that SPICE uses; for default, the program chooses
    either TSTEP or (TSTOP-TSTART)/50.0, whichever is smaller. TMAX is useful
    when one wishes to guarantee a computing interval which is smaller than
    the printer increment, TSTEP.
    UIC (use initial conditions) is an optional keyword which indicates that
    the user does not want SPICE to solve for the quiescent operating point
    before beginning the transient analysis. If this keyword is specified,
    SPICE uses the values specified using IC=... on the various elements as
    the initial transient condition and proceeds with the analysis. If the
    .IC control line has been specified, then the node voltages on the .IC
    line are used to compute the initial conditions for the devices. Look at
    the description on the .IC control line for its interpretation when UIC
    is not specified.
    '''

    # determine the time-series array length and setup the circuit:
    n = int(tstop / tstep) + 1
    self.circuit.setup(tstep)

    # allocate the output arrays:
    self.trans_data = numpy.zeros((self.circuit.nodes, n)) # matrix for output
    self.trans_time = numpy.zeros(n) # array for time values

    # step through time evolution of the network and save off across data
    # for each timestep:
    self.time = 0.0
    for i in range(n):
      self.circuit.step(tstep)
      self.time += tstep
      self.trans_time[i] = (i * tstep) # add absolute time value for this step
      self.trans_data[:,i] = numpy.copy(self.circuit.across) # add across data for this step

  def save(self):
    pass
  
  def _print(self): # must be _print to avoid collisions with Python builtin print
    pass

  def plot(self, pltype, *variables):
    '''.PLOT Lines
    General form:
    .PLOT PLTYPE OV1 <(PLO1, PHI1)> &ltOV2; <(PLO2, PHI2)> ... OV8>
    Examples:
    .PLOT DC V(4) V(5) V(1)
    .PLOT TRAN V(17, 5) (2, 5) I(VIN) V(17) (1, 9)
    .PLOT AC VM(5) VM(31, 24) VDB(5) VP(5)
    .PLOT DISTO HD2 HD3(R) SIM2
    .PLOT TRAN V(5, 3) V(4) (0, 5) V(7) (0, 10)
    The Plot line defines the contents of one plot of from one to eight output 
    variables. PLTYPE is the type of analysis (DC, AC, TRAN, NOISE, or DISTO) for 
    which the specified outputs are desired. The syntax for the OVI is identical
    to that for the .PRINT line and for the plot command in the interactive mode.
    The overlap of two or more traces on any plot is indicated by the letter X.
    When more than one output variable appears on the same plot, the first variable
    specified is printed as well as plotted. If a printout of all variables is
    desired, then a companion .PRINT line should be included.
    There is no limit on the number of .PLOT lines specified for each type of
    analysis.
    '''
    if pltype.lower() == 'tran': # If the plot type is transient. (TODO: other types)
      for variable in variables: # for each plottable variable:
        trace = None
        label = ''
        if isinstance(variable, Voltage): # if the plottable is a voltage:
          trace = self.trans_data[variable.node1,:] - self.trans_data[variable.node2,:]
          if variable.node2 == 0:
            label = 'V({0:d})'.format(variable.node1)
          else:
            label = 'V({0:d},{1:d})'.format(variable.node1, variable.node2)
        elif isinstance(variable, Current): # if the plottable is a current:
          sensor_device = self.circuit.devices[variable.vsource]
          if isinstance(sensor_device, CurrentSensor):
            trace = -self.trans_data[sensor_device.get_current_node(),:]
            label = 'I({0})'.format(variable.vsource)
        if trace is not None:
          plt.plot(self.trans_time, trace, label=label)# crate a matplotlib plot

      plt.title(self.circuit.title1)
      plt.legend()
      plt.show()

    pass

  def four(self):
    '''
    Not implemented.
    '''
    pass








