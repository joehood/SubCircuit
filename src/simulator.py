"""Contains the functions for analysis and simulation for a SPICE network."""

from __future__ import print_function, division
import matplotlib.pyplot as plt
import numpy
from interfaces import *

try:
    import wx
    from src import editor
except:
    pass


class Simulator():
    """Represents a SPICE simulator.
    Provides the functions for SPICE simulation and analysis.
    """

    def __init__(self, netlist, maxitr=100, tol=0.001):
        """
        Creates a new Simulator instance for the provided circuit.
        Arguments:
        :param circuit: The circuit to simulate.
        """
        self.netlist = netlist
        self.netlist.simulator = self
        self.t = 0.0
        self.tmax = 0.0
        self.maxitr = maxitr
        self.tol = tol
        self.trans_data = None
        self.trans_time = None

    def ac(self):
        raise NotImplementedError()

    def dc(self):
        raise NotImplementedError()

    def distro(self):
        raise NotImplementedError()

    def noise(self):
        raise NotImplementedError()

    def op(self):
        raise NotImplementedError()

    def pz(self):
        raise NotImplementedError()

    def sens(self):
        raise NotImplementedError()

    def tf(self):
        raise NotImplementedError()

    def trans(self, tstep, tstop, tstart=None, tmax=None, uic=False):

        """SPICE .TRAN command (Transient Analysis)
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
        >TSTART;, TSTOP>, the circuit is analyzed and outputs are stored. TMAX
        is the maximum stepsize that SPICE uses; for default, the program
        chooses either TSTEP or (TSTOP-TSTART)/50.0, whichever is smaller.
        TMAX is useful when one wishes to guarantee a computing interval which
        is smaller than the printer increment, TSTEP. UIC (use initial
        conditions) is an optional keyword which indicates that the user does
        not want SPICE to solve for the quiescent operating point before
        beginning the transient analysis. If this keyword is specified,
        SPICE uses the values specified using IC=... on the various elements as
        the initial transient condition and proceeds with the analysis. If the
        .IC control line has been specified, then the node voltages on the .IC
        line are used to compute the initial conditions for the devices. Look at
        the description on the .IC control line for its interpretation when UIC
        is not specified.

        :param tstep: Time step in seconds
        :param tstop: Simulation stop time in seconds
        :param tstart: TODO
        :param tmax: TODO
        :param uic: Flag for use initial conditions
        :return: None
        """

        # determine the time-series array length and setup the circuit:
        n = int(tstop / tstep) + 1
        self.netlist.setup(tstep)
        self.tmax = tstop

        # allocate the arrays and save to variables for plot():
        self.trans_data = numpy.zeros((self.netlist.nodenum, n))
        self.trans_time = numpy.zeros(n)  # array for time values

        # step through time evolution of the network and save off across data
        # for each timestep:
        self.t = 0.0
        p1 = 0.0
        p0 = p1
        step = 0.05

        itr = []

        for i in range(n):

            self.netlist.simulation_hook(tstep, self.t)
            for device in self.netlist.devices.values():
                device.update()

            success, k = self.netlist.step(tstep, self.t)
            itr.append(k)
            if not success:
                print("Error solving circuit. Simulation not completed.")
                break
            self.t += tstep
            self.trans_time[i] = (i * tstep)
            self.trans_data[:, i] = numpy.copy(self.netlist.across)
            p1 = i / n
            if p1 - p0 >= step:
                p0 = p1
                s = "time:{0:8.4g}s percent:{1:3.0f} min itr: {2}  max itr: {3}"
                s = s.format(self.t, p1*100, min(itr), max(itr))
                itr = []
                print(s)

    def save(self):
        raise NotImplementedError()

    def print_(self):
        raise NotImplementedError()

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

        notebook = None
        if 'notebook' in kwargs:
            notebook = kwargs['notebook']
        plot_panel = None

        curves = []
        for variable in variables:
            trace = None
            label = ''
            if isinstance(variable, Voltage):
                node1_index = self.netlist.nodes[variable.node1]
                node2_index = self.netlist.nodes[variable.node2]
                trace = (self.trans_data[node1_index, :] -
                         self.trans_data[node2_index, :])
                if variable.node2 == 0:
                    label = 'V({0})'.format(variable.node1)
                else:
                    s = 'V({0}, {1})'
                    label = s.format(variable.node1, variable.node2)
            elif isinstance(variable, Current):
                device = self.netlist.devices[variable.vsource]
                if isinstance(device, CurrentSensor):
                    node, scale = device.get_current_node()
                    trace = self.trans_data[node, :] * scale
                    label = 'I({0})'.format(variable.vsource)
            if trace is not None:
                curves.append((self.trans_time, trace, label))

        if notebook:
            plot_panel = editor.PlotPanel(notebook)
            notebook.AddPage(plot_panel, 'Plot', True)
            plot_panel.set_data(curves)
            plot_panel.draw()

        else:
            plt.figure()
            for curve in curves:
                x, y, label = curve
                plt.plot(x, y, label=label)
                plt.title(self.netlist.title)
                plt.legend()
                plt.xlabel('t (s)')
            if curves:
                plt.show()

        return plot_panel

    def four(self):
        raise NotImplementedError()

    def get_current_time(self):
        """Get the current simulation time in seconds
        :return: The current simualtion time in seconds
        """
        return self.t


if __name__ == '__main__':
    pass  # todo: test code here

