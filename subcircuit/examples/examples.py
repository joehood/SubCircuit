"""Examples

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

from subcircuit.netlist import *


# netlist = Netlist("Series RLC")
# netlist.device('V1', V((1, 0), Sin(0.0, 1.0, 100.0)))
# netlist.device('R1', R((1, 2), 1.0))
# netlist.device('L1', L((2, 3), 0.001, ic=0.0))
# netlist.device('C1', C((3, 0), 0.001, ic=0.0))
# netlist.trans(0.0001, 0.05)
# netlist.plot('tran', Voltage(2), Voltage(3), Current('V1'))

#
# def example2():
#   circuit = ps.Circuit()
#   circuit.title = 'Half-wave Rectifier'
#   circuit.add_device('V1', ps.V, 1, 0, 4, ps.Sin(0.0, 1.0, 100.0))
#   circuit.add_device('R1', ps.R, 1, 2, 0.2)
#   circuit.add_device('D1', ps.D, 2, 3, 'Diode1')
#   circuit.add_device('R2', ps.R, 3, 0, 2.0)
#   circuit.add_device('C1', ps.C, 3, 0, 0.01)
#   circuit.add_model('Diode1', ps.DMod, IS=1.0e-9)
#
#   simulator = ps.Simulator(circuit)
#   circuit.trans(0.0002, 0.1)
#   circuit.plot('tran', ps.Voltage(1), ps.Voltage(3))
#

# netlist = Netlist("Full-wave Rectifier")
# netlist.device('V1', V((2, 3), Sin(0.0, 10.0, 100.0)))
# netlist.device('D1', D((2, 1)))
# netlist.device('D2', D((3, 1)))
# netlist.device('D3', D((4, 2)))
# netlist.device('D4', D((4, 3)))
# netlist.device('R1', R((5, 4), 10.0))
# netlist.device('R2', R((4, 0), 1000.0))
# netlist.device('C1', C((5, 4), 0.002))
# netlist.device('L1', L((1, 5), 0.00001))
# netlist.trans(0.0001, 0.02)
# netlist.plot(Voltage(2, 3), Voltage(5, 4), Current('V1'))


"""
Example Transformer (SPICE Netlist)
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

# netlist = Netlist("Example Transformer (Subcircuit Netlist)")
# netlist.device("V1N", V((1, 0), Sin(0, 170, 60, 0, 0)))
# netlist.device("L1", L((1, 0), 2000))
# netlist.device("L2", L((2, 0), 200))
# netlist.device("K1", K('L1', 'L2', 0.99999))
# netlist.device("RL", R((2, 0), 500.0))
# netlist.trans(0.00002, 0.025)
# netlist.plot(Voltage(1), Voltage(2))



#
# circuit = ps.Circuit()
# circuit.title = 'Diode Test'
# circuit.add_model(ps.DMod('Diode1', IS=1.0e-9))
# circuit.add_device(ps.V('V1', 1, 0, 2, ps.Pulse(v1=0.0, v2=1.0, td=0.1, tr=0.1, tf=0.2, pw=0.5, per=1.0)))
# circuit.add_device(ps.D('D1', 1, 3, 'Diode1'))
# circuit.add_device(ps.R('R1', 3, 0, value=1.0))
# simulator = ps.Simulator(circuit)
# simulator.trans(0.02, 4.0)
# simulator.plot('tran', ps.Voltage(1), ps.Current('V1'))

# circuit = ps.Circuit()
# circuit.title = 'Switch Test'
# circuit.add_device(ps.V('V1', 1, 0, 2, ps.Pulse(v1=0.0, v2=1.0, pw=0.5, per=1.0)))
# circuit.add_device(ps.R('R0', 1, 0, value=1000.0))
# circuit.add_device(ps.V('V2', 3, 0, 4, value=10.0))
# circuit.add_device(ps.R('R1', 3, 5, value=2.0))
# circuit.add_device(ps.S('S1', [5, 6, 7], vsource='V1', vt=0.5))
# circuit.add_device(ps.R('R2', 6, 0, value=2.0))
# simulator = ps.Simulator(circuit)
# simulator.trans(0.01, 4.0)
# simulator.plot('tran', ps.Voltage(3), ps.Voltage(7))  # ps.Current('V1'))

# cir = ps.Circuit("Switch Test")
#
# V1 = ps.V('V1', 1, 0, 4, value=10.0)
# Vs = ps.V('Vs', 3, 0, 5, ps.Sin(0.0, 10.0, 10.0))
# S1 = ps.S('S1', (1, 2, 6), vsource='Vs')
# R1 = ps.R('R1', 2, 0, value=10.0)
#
# cir.add_devices(V1, Vs, S1, R1)
#
# sim = ps.Simulator(cir)
#
# sim.trans(0.01, 1.0)
#
# sim.plot('tran',
#          ps.Voltage(2),
#          ps.Voltage(3))


"""
Boost Converter Example


                   .-------------.
                  _|_            |
                  /_\  D         |
                   |             |
     1     L     2 |             | 3
     .---()()()----o         .---o--.
    +|    (5)      |         |      |
    ,-.            |        [ ]    _|_
 V ( = )(4)     (6) / S     | |R   ___ C
    `-'            o        [ ]     |
     |             |         |      |
     '-------------o---------o------'
                  _|_
                   -
     7
     o
   + |
    ,-.
VC (-_-)(8)
    `-'
    _|_
     -


"""

# circuit = ps.Circuit()
# circuit.title = 'Boost Converter'
#
# circuit.add_device(ps.V('VC', 7, 0, 8,
#                         ps.Pulse(v1=0.0, v2=1.0, pw=0.0005, per=0.001)))
#
# circuit.add_device(ps.V('V', 1, 0, 4, value=100.0))
# circuit.add_device(ps.L('L', 1, 2, 5, value=0.001))
# circuit.add_device(ps.S('S', (2, 0, 6), vsource='VC', vt=0.5))
# circuit.add_device(ps.D('D', 2, 3))
# circuit.add_device(ps.R('R', 3, 0, value=10.0))
# circuit.add_device(ps.C('C', 3, 0, value=0.0001))
# simulator = ps.Simulator(circuit)
# simulator.trans(0.0001, 0.01)
# simulator.plot('tran',
#                ps.Voltage(2),
#                ps.Voltage(2),
#                ps.Current('L'))


"""
Three-phase Rectifier:
                                 4           Lf     6
                          .------o------o---UUUU----.
                          |      |      |           |
                         _|_    _|_    _|_          |
                         /_\ D1 /_\ D3 /_\ D5       o-------.
                          |      |      |           |       |
    .---------------------o 1    |      |           |       |
    |                     |      |      |          .-.     _|_
    |       .--------------------o 2    |          | |RL   ___ Cf
    |       |             |      |      |          | |      |
    |       |       .-------------------o 3        '-'      |
   +|      +|      +|     |      |      |           |       |
   ,'.     ,'.     ,'.    |      |      |           |       |
Va( ~ ) Vb( ~ ) Vc( ~ )   |      |      |           o-------'
   `.'     `.'     `.'   _|_    _|_    _|_          |
    |       |       |    /_\ D2 /_\ D4 /_\ D6       |
    '-------+-------'     |      |      |           |
       0   _|_            '------o------o-----------'
            -                       5

"""

# netlist = Netlist("Three-phase Rectifier")
#
# a = 2.0 / 3.0 * math.pi
#
# netlist.device("Va", V((1, 0), Sin(va=80.0, freq=60.0, phi=0), res=0, induct=0))
# netlist.device("Vb", V((2, 0), Sin(va=80.0, freq=60.0, phi=a), res=0, induct=0))
# netlist.device("Vc", V((3, 0), Sin(va=80.0, freq=60.0, phi=-a), res=0, induct=0))
# netlist.device("D1", D((1, 4)))
# netlist.device("D3", D((2, 4)))
# netlist.device("D5", D((3, 4)))
# netlist.device("D2", D((5, 1)))
# netlist.device("D4", D((5, 2)))
# netlist.device("D6", D((5, 3)))
# netlist.device("RL", R((6, 5), 10.0))
# netlist.device("Cf", C((6, 5), 0.0001))
# netlist.device("Lf", L((4, 6), 0.0001))
#
# netlist.simulator.tol = 0.1
#
#
# def load_step(dt, t):
#     if 0.02 < t < 0.04:
#         netlist.devices['RL'].value = 2.0
#     elif t > 0.04:
#         netlist.devices['RL'].value = 1.0
#
# netlist.simulation_hook = load_step
#
# netlist.trans(0.0001, 0.05)
# netlist.plot(Voltage(1),
#              Voltage(2),
#              Voltage(3),
#              Current('Va'),
#              Current('Vb'),
#              Current('Vc'),
#              Current('Lf'),
#              Voltage(4, 5))


"""
Three-phase Inverter
                                 2           Lf     1
                          .------o------o-------------.
                          |      |      |             |
                          o      o      o             |
                        S1 \   S3 \   S5 \            |
                          |      |      |             |
    .---------------------o 4    |      |             | +
    |                     |      |      |            ,-.
    |       .-------------|------o 5    |           ( = ) Vdc
    |       |             |      |      |            `-'
    |       |       .-----|------|------o 6           |
    |       |       |     |      |      |             |
   .-.     .-.     .-.    |      |      |             |
 Ra| |   Rb| |   Rc| |    |      |      |             |
   '-'     '-'     '-'    o      o      o             |
    |       |       |      \S2    \S4    \S6          |
    '-------+-------'     |      |      |             |
       0   _|_            '------o------o-------------'
            -                       3

"""

# alpha = 2.0 / 3.0 * math.pi
#
# cir = ps.Circuit()
#
# cir.title = "Three-phase Inverter"
#
# Vdc = ps.V('Va', 1, 0, 7, 150.0)
#
# Vs1 = ps.V('Vs', 14, 0, 15, ps.Sin(0.0, 1.0, 60.0, phi=0.0))
# Vs3 = ps.V('Vs', 16, 0, 17, ps.Sin(0.0, 1.0, 60.0, phi=alpha))
# Vs5 = ps.V('Vs', 18, 0, 19, ps.Sin(0.0, 1.0, 60.0, phi=-alpha))
# Vs2 = ps.V('Vs', 20, 0, 21, ps.Sin(0.0, 1.0, 60.0, phi=0.0))
# Vs4 = ps.V('Vs', 22, 0, 23, ps.Sin(0.0, 1.0, 60.0, phi=alpha))
# Vs6 = ps.V('Vs', 24, 0, 25, ps.Sin(0.0, 1.0, 60.0, phi=-alpha))
#
# Vt = ps.V('Vt', 26, 0, 27,
#           ps.Pulse(v1=-1, v2=1, tr=0.001, tf=0.001, pw=0.0, per=0.002))
#
# Ec = ps.E('Ec', 28, 0, 2, 1, 29,
#            value=ps.Table((-0.00001, 0.0), (0.00001, 1.0e12)), limit=1.0)
#
# Rca = ps.R('RL', 3, 0, 0.001)
#
# S1 = ps.S('S1', (2, 4, 8), vsource='Rca')
# S3 = ps.S('S3', (2, 5, 9), vsource='Vs3')
# S5 = ps.S('S5', (2, 6, 10), vsource='Vs5')
# S2 = ps.S('S2', (4, 3, 11), vsource='Vs2')
# S4 = ps.S('S4', (5, 3, 12), vsource='Vs4')
# S6 = ps.S('S6', (6, 3, 13), vsource='Vs6')
#
# Ra = ps.R('Ra', 4, 0, 100.0)
# Rb = ps.R('Rb', 5, 0, 100.0)
# Rc = ps.R('Rc', 6, 0, 100.0)
#
# cir.add_devices(Vdc, Vt, Vsa, Vsb, Vsc, S1, S2, S3, S4, S5, S6, Ra, Rb, Rc)
#
# sim = ps.Simulator(cir)
# sim.trans(0.0005, 0.1)
#
# sim.plot('tran',
#          ps.Voltage(1),
#          ps.Voltage(2),
#          ps.Voltage(3),
#          ps.Voltage(6, 5))

"""
PWM Test

       1          .--------.    3
     .------------|        |------.
     |            |        |     [ ]
    ,-.       2   |  Ec    |     | | RL
Vt ( ^ )(4)  .----|  (6)   |     [ ]
    `-'      |    |        |---.--'
    _|_     ,-.   '--------'  _|_
     -  Vs ( ~ )(5)               -
            `-'
            _|_
             -
"""


# cir = ps.Circuit("Saw Wave Stimulus Test and VCVS (E) Test")
#
# Vt = ps.V('Vt', 1, 0, 7,
#           ps.Pulse(v1=-1, v2=1, tr=0.001, tf=0.001, pw=0.0, per=0.002))
#
# Vs = ps.V('Vs', 2, 0, 8,
#           ps.Sin(0.0, 1.0, 60.0))
#
# Ec = ps.E('Ec', 3, 0, 2, 1, 9,
#           ps.Table((-0.00001, 0.0), (0.00001, 1.0e12)), limit=1.0)
#
# Vg = ps.V('Vg', 4, 0, 10, value=100.0)
#
# Sg = ps.S('Sg', (4, 5, 11), vsource='Ec', vt=0.0)
#
# Rg = ps.R('Rg', 6, 0, value=10.0)
#
# Lg = ps.L('Lg', 5, 6, 12, 0.001)
#
# Cg = ps.C('Cg', 6, 0, 0.0001)
#
#
# cir.add_devices(Vt, Vs, Ec, Vg, Sg, Rg, Cg, Lg)
#
# sim = ps.Simulator(cir)
#
# sim.trans(0.0001, 0.1)
#
# sim.plot('tran',
#          ps.Voltage(2),
#          ps.Voltage(3),
#          ps.Voltage(6))


# # create netlist and add a title:
# netlist = Netlist('Subcircuit Test')
#
# # define a subcircuit definition:
# rdiv = netlist.subckt('rdiv', Subckt([1, 2], r1=10.0, r2=20.0))
# rdiv.device('L', L([1, 3], value=0.01))
# rdiv.device('R', R([3, 2], value=10.0))
# rdiv.device('C', C([1, 2], value=0.0001))
#
# # add devices and subcircuit instances to circuit:
# netlist.device('V1', V(['input', 'ground'], value=Sin(0.0, 10.0, 60.0)))
# netlist.device('X1', X(['input', 'ground'], subckt='rdiv'))
#
# # run the transient simulation and plot some variables:
# netlist.trans(0.0001, 0.1)
#
# netlist.plot(Voltage('input'),
#              Voltage('X1_3'),
#              Current('V1'),
#              Current('X1_L'))


netlist = Netlist("Distributed Tline")

# # define section subckt:
# section = netlist.subckt('section', Subckt((1, 2)))
# section.device('L', L((1, 2), 0.001))
# section.device('C', C((2, 0), 0.0001))
#
# # source:
# netlist.device('V1', V((1, 0), Sin(0.0, 100.0, 60.0)))
#
# # add 6 sections:
# for i in range(1, 8):
#     name = "X{0}".format(i)
#     netlist.device(name, X((i, i+1), subckt='section'))
#
# # load:
# netlist.device('R1', R((8, 0), 5.0))
#
# # transient simulation:
# netlist.trans(0.0001, 0.1)
#
# # plot all voltages:
# voltages = []
# for i in range(1, 9):
#     voltages.append(Voltage(i))
#
# netlist.plot(*voltages)

