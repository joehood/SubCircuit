PySpyce Circuit Simulator
=========================


![alt text](https://github.com/josephmhood/PySpyce/blob/master/Artwork/screenshot_9.png "")


Python Implementation of SPICE Circuit Simulator. 

Requires Python 2.7, Scipy Stack and wxPython.

*Note: Many devices are not yet implemented. This is currently at a proof-of-concept phase. The devices and circuits shown in these examples are all currently supported and working.*

I'm looking for someone with Python and EE experience to help develop the rest of the atomic SPICE elements.


##Graphical and Programmatic Netlist Creation and Simulation

PySpyce allows the creation of netlists through a schematic editor or directly with a Python script.


###Graphical Example:###

![alt text](https://github.com/josephmhood/PySpyce/blob/master/Artwork/screenshot_10.png "")


###Programmatic Netlist Development:###

```python
netlist = Netlist("Distributed Tline")

# define section subckt:
section = netlist.subckt('section', Subckt((1, 2)))
section.device('L', L((1, 2), 0.001))
section.device('C', C((2, 0), 0.0001))

# source:
netlist.device('V1', V((1, 0), Sin(0.0, 100.0, 60.0)))

# add 6 sections:
for i in range(1, 8):
    name = "X{0}".format(i)
    netlist.device(name, X((i, i+1), subckt='section'))

# load:
netlist.device('R1', R((8, 0), 5.0))

# transient simulation:
netlist.trans(0.0001, 0.1)

# plot all voltages:
voltages = []
for i in range(1, 9):
    voltages.append(Voltage(i))

netlist.plot(*voltages)
```
![alt text](https://github.com/josephmhood/PySpyce/blob/master/Artwork/screen_5.png "")


###Or Build Netlists Just As You Would in SPICE:###

```python
# SPICE Netlist:

""" 
Example Transformer
VIN 1 0 SIN(0 170 60 0 0)
L1 1 0 2000
L2 2 0 200
K1 L1 L2 0.99999
RL 2 0 500
.TRAN 0.2M 25M
.PLOT TRAN V(1)
.PLOT TRAN V(2)
.END
"""

# Equivalent PySpyce Netlist:

netlist = Netlist("Example Transformer")
netlist.device("V1N", V((1, 0), Sin(0, 170, 60, 0, 0)))
netlist.device("L1", L((1, 0), 2000))
netlist.device("L2", L((2, 0), 200))
netlist.device("K1", K('L1', 'L2', 0.99999))
netlist.device("RL", R((2, 0), 500.0))
netlist.trans(0.00002, 0.025)
netlist.plot(Voltage(1), Voltage(2))
```

###Custom Device Creation###

Defining a device and it's schematic object is straight-forward. Here is an example (Voltage source):

```python
class VBlock(Block):
    def __init__(self, name):

        # init super:
        Block.__init__(self, name, V)

        # ports:
        self.ports['positive'] = Port(self, 0, (50, 0))
        self.ports['negative'] = Port(self, 1, (50, 100))

        # properties:
        self.properties['Voltage (V)'] = 1.0

        # leads:
        self.lines.append(((50, 0), (50, 25)))
        self.lines.append(((50, 75), (50, 100)))

        # plus:
        self.lines.append(((50, 33), (50, 43)))
        self.lines.append(((45, 38), (55, 38)))

        # circle
        self.circles.append((50, 50, 25))

    def get_engine(self, nodes):
        return V(nodes, self.properties['Voltage (V)'])
        
        
        
class V(Device, CurrentSensor):

    def __init__(self, nodes, value, res=0.0, induct=0.0, **kwargs):
    
        Device.__init__(self, nodes, 1, **kwargs)

        # determine type of value provided:
        if isinstance(value, Stimulus):
            self.stimulus = value
            self.stimulus.device = self
        elif isinstance(value, float) or isinstance(value, int):
            self.stimulus = None
            self.value = float(value)

        self.res = res
        self.induct = induct

    def connect(self):
        nplus, nminus = self.nodes
        self.port2node = {0: self.get_node_index(nplus),
                          1: self.get_node_index(nminus),
                          2: self.create_internal("{0}_int".format(self.name))}

    def start(self, dt):

        self.jac[0, 2] = 1.0
        self.jac[1, 2] = -1.0
        self.jac[2, 0] = 1.0
        self.jac[2, 1] = -1.0
        self.jac[2, 2] = -(self.res + self.induct / dt)

        volt = 0.0
        if self.stimulus:
            volt = self.stimulus.start(dt)
        elif self.value:
            volt = self.value

        self.bequiv[2] = volt

    def step(self, dt, t):

        if self.stimulus:
            volt = self.stimulus.step(dt, t)
        else:
            volt = self.value

        if self.induct:
            il = self.get_across_history(2)
            volt += self.induct / dt * il

        self.bequiv[2] = volt

    def get_current_node(self):
        return self.port2node[2]
```

