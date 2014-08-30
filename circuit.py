"""Contains Circuit and SubCircuit class definitions."""

from __future__ import print_function
import interfaces
import simulator
import numpy
import numpy.linalg as la


class SubCircuit():
    """A SPICE subcircuit (.subckt) object. """

    def __init__(self, parent):
        """Creates an empty SubCircuit.

        Arguments:
        parent -- the parent circuit or subcircuit.
        name   -- optional name.
        """
        self.nodes = {0: 0, 'ground': 0, 'gnd': 0}  # pre-load with ground node
        self.nodenum = 1
        self.internalnum = 0
        self.across = None  # across at current time and iteration
        self.across_last = None  # across at last iteration
        self.across_history = None  # across at end of last time step
        self.jac = None
        self.bequiv = None
        self.devices = {}
        self.converged = False
        self.simulator = None
        self.dt = 0.0

    def stamp(self):
        """Creates matrix stamps for the subcircuit network scope by stamping
        the devices together that belong to this subcircuit.
        """
        self.jac[:, :] = 0.0
        self.bequiv[:] = 0.0
        for device in self.devices.values():
            for pi, ni in device.nodes.items():
                self.bequiv[ni] += device.bequiv[pi]
                for pj, nj in device.nodes.items():
                    self.jac[ni, nj] += device.jac[pi, pj]
        dummy = False

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
        for device in self.devices.values():
            device.setup(dt)

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
        if 1:
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
        for device in self.devices.values():
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
        key = key.lower()  # node keys are not case sensitive
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

    def add(self, name, device):
        """Device factory and loader.
        """
        if not name in self.devices:
            self.devices[name] = device
            device.name = name
            device.subcircuit = self
            device.map_nodes()



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

    def __init__(self, title=''):
        """Creates a circuit object."""
        SubCircuit.__init__(self, parent=None)
        self.models = {}
        self.title = title
        self.simulator = simulator.Simulator(self)

    def add_model(self, model):
        """Add a model (.model) definition to the Circuit."""
        self.models[model.name] = model

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
        self.simulator.trans(tstep, tstop, tstart, tmax, uic)

    def plot(self, *variables, **kwargs):
        """.PLOT Lines
        General form:
        .PLOT PLTYPE OV1 <(PLO1, PHI1)> <OV2; <(PLO2, PHI2)> ... OV8>
        Examples:
        .PLOT DC V(4) V(5) V(1)
        .PLOT TRAN V(17, 5) (2, 5) I(VIN) V(17) (1, 9)
        .PLOT AC VM(5) VM(31, 24) VDB(5) VP(5)
        .PLOT DISTO HD2 HD3(R) SIM2
        .PLOT TRAN V(5, 3) V(4) (0, 5) V(7) (0, 10)
        The Plot line defines the contents of one plot of from one to eight
        output variables. PLTYPE is the type of analysis (DC, AC, TRAN, NOISE,
        or DISTO) for which the specified outputs are desired. The syntax for
        the OVI is identical to that for the .PRINT line and for the plot
        command in the interactive mode. The overlap of two or more traces on
        any plot is indicated by the letter X. When more than one output
        variable appears on the same plot, the first variable specified is
        printed as well as plotted. If a printout of all variables is desired,
        then a companion .PRINT line should be included. There is no limit on
        the number of .PLOT lines specified for each type of analysis.

        :param variables: Plottables. Example: Voltage(1,2), Current('VSENSE')
        :param kwargs: TODO
        :return: None
        """
        return self.simulator.plot(self, *variables, **kwargs)



