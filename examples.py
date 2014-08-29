import pyspyce as ps
import math


# def example1():
# circuit = ps.Circuit()
# circuit.title = 'Series RLC'
# circuit.add_device(ps.V, 1, 0, 4, ps.Sin(0.0, 1.0, 100.0))
# circuit.add_device('R1', ps.R, 1, 2, 1.0)
# circuit.add_device('L1', ps.L, 2, 3, 5, 0.01, ic=0.0)
# circuit.add_device('C1', ps.C, 3, 0, 0.001, ic=0.0)
#
# simulator = ps.Simulator(circuit)
#   simulator.trans(0.0005, 0.05)
#   simulator.plot('tran', ps.Voltage(2), ps.Voltage(3), ps.Current('V1'))
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

# circuit = ps.Circuit()
# circuit.title = 'Full-wave Rectifier'
# circuit.add_device(ps.V('V1', 2, 3, 6, ps.Sin(0.0, 10.0, 100.0)))
# circuit.add_device(ps.D('D1', 2, 1, 'Diode1'))
# circuit.add_device(ps.D('D2', 3, 1, 'Diode1'))
# circuit.add_device(ps.D('D3', 4, 2, 'Diode1'))
# circuit.add_device(ps.D('D4', 4, 3, 'Diode1'))
# circuit.add_device(ps.R('R1', 5, 4, 10.0))
# circuit.add_device(ps.R('R2', 4, 0, 1000.0))
# circuit.add_device(ps.C('C1', 5, 4, 0.002))
# circuit.add_device(ps.L('L1', 1, 5, 7, 0.0001))
# circuit.add_model(ps.DMod('Diode1', IS=1.0e-2))
# simulator = ps.Simulator(circuit)
# simulator.trans(0.0001, 0.04)
# simulator.plot('tran', ps.Voltage(2, 3), ps.Voltage(5, 4), ps.Current('V1'))
#
#
# circuit = ps.Circuit()
# circuit.title = 'Mutual Inductance Test'
#
# circuit.add_device(ps.V('V1', 1, 0, 5, ps.Sin(0.0, 10.0, 100.0)))
# circuit.add_device(ps.R('R1', 1, 2, 0.01))
# circuit.add_device(ps.L('L1', 2, 0, 6, 0.001))
# circuit.add_device(ps.L('L2', 3, 0, 7, 0.002))
# circuit.add_device(ps.K('K1', 'L1', 'L2', 0.999))
# circuit.add_device(ps.R('R2', 3, 4, 10.0))
# circuit.add_device(ps.V('VS',  0, 4, 8, 0.0))
#
# simulator = ps.Simulator(circuit)
#
# simulator.trans(0.0001, 0.05)
#
# simulator.plot('tran',
#                ps.Voltage(1),
#                ps.Voltage(3),
#                ps.Current('V1'),
#                ps.Current('VS'))
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


"""
Boost Converter Example

    1   L   2   D        3
    .--uuu--o--->|---o-----.
   +|   5   |        |     |
  V( )4    6 /S(VC) [ ]R  === C
    |       |        |     |
    '-------o--------o-----'
            0

    7   RC
    .--vvv--.
   +|       |
 VC( )8     |
    |       |
    '-------'
        0

"""
# circuit = ps.Circuit()
# circuit.title = 'Boost Converter'
# circuit.add_device(ps.V('VC', 7, 0, 8, ps.Pulse(v1=0.0, v2=1.0, pw=0.0005, per=0.001)))
# circuit.add_device(ps.R('RC', 7, 0, value=100.0))
# circuit.add_device(ps.V('V', 1, 0, 4, value=12.0))
# circuit.add_device(ps.L('L', 1, 2, 5, value=0.0001))
# circuit.add_device(ps.S('S', [2, 0, 6], vsource='VC', vt=0.5))
# circuit.add_device(ps.D('D', 2, 3))
# circuit.add_device(ps.R('R', 3, 0, value=10.0))
# circuit.add_device(ps.C('C', 3, 0, value=0.001))
# simulator = ps.Simulator(circuit)
# simulator.trans(0.0001, 0.1)
# simulator.plot('tran', ps.Voltage(3)) #, ps.Current('V'))


# # Three-phase Rectifier:
#
# """
#                                  4           Lf     6
#                           .------o------o---UUUU----.
#                           |      |      |           |
#                          _|_    _|_    _|_          |
#                       D1 /_\ D3 /_\ D5 /_\          o-------.
#                           |      |      |           |       |
#     .---------------------o 1    |      |           |       |
#     |                     |      |      |          .-.     _|_
#     |       .-------------|------o 2    |          | |RL   ___ Cf
#     |       |             |      |      |          | |      |
#    +|      +|      +.-----|------|------o 3        '-'      |
#     |       |       |     |      |      |           |       |
#    ,'.     ,'.     ,'.    |      |      |           o-------'
# Va(   ) Vb(   ) Vc(   )   |      |      |           |
#    `.'     `.'     `.'   _|_    _|_    _|_          |
#     |       |       |    /_\ D2 /_\ D4 /_\ D6       |
#     '-------+-------'     |      |      |           |
#        0   _|_            '------o------o-----------'
#             -                       5
#
# """
#
# alpha = 2.0 / 3.0 * math.pi
#
# cir = ps.Circuit()
#
# cir.title = "Three-phase Rectifier"
#
# Va = ps.V('Va', 1, 0, 7, ps.Sin(va=80.0, freq=60.0, phi=0.0))
# Vb = ps.V('Vb', 2, 0, 8, ps.Sin(va=80.0, freq=60.0, phi=alpha))
# Vc = ps.V('Vc', 3, 0, 9, ps.Sin(va=80.0, freq=60.0, phi=-alpha))
#
# D1 = ps.D('D1', 1, 4)
# D3 = ps.D('D3', 2, 4)
# D5 = ps.D('D5', 3, 4)
# D2 = ps.D('D2', 5, 1)
# D4 = ps.D('D4', 5, 2)
# D6 = ps.D('D6', 5, 3)
#
# RL = ps.R('RL', 6, 5, 100.0)
# Cf = ps.C('Cf', 6, 5, 0.001)
# Lf = ps.L('Lf', 4, 6, 10, 0.001)
#
# cir.add_devices(Va, Vb, Vc, D1, D2, D3, D4, D5, D6, RL, Cf, Lf)
#
# sim = ps.Simulator(cir)
# sim.trans(0.0005, 0.1)
#
# sim.plot('tran',
#          ps.Voltage(1),
#          ps.Voltage(2),
#          ps.Voltage(3),
#          ps.Voltage(6, 5))
#
#
# # Three-phase Inverter:
#
# """
#                                  2           Lf     1
#                           .------o------o-------------.
#                           |      |      |             |
#                           o      o      o             |
#                         S1 \   S3 \   S5 \            |
#                           |      |      |             |
#     .---------------------o 4    |      |             | +
#     |                     |      |      |            ,-.
#     |       .-------------|------o 5    |           (   ) Vdc
#     |       |             |      |      |            `-'
#     |       |       .-----|------|------o 6           |
#     |       |       |     |      |      |             |
#    .-.     .-.     .-.    |      |      |             |
#  Ra| |   Rb| |   Rc| |    |      |      |             |
#    '-'     '-'     '-'    o      o      o             |
#     |       |       |      \S2    \S4    \S6          |
#     '-------+-------'     |      |      |             |
#        0   _|_            '------o------o-------------'
#             -                       3
#
# """
#
# alpha = 2.0 / 3.0 * math.pi
#
# cir = ps.Circuit()
#
# cir.title = "Three-phase Inverter"
#
# Vdc = ps.V('Va', 1, 0, 7, 150.0)
#
# S1 = ps.S('S1', 2, 4)
# S3 = ps.S('S3', 2, 5)
# S5 = ps.S('S5', 2, 6)
# S2 = ps.S('S2', 4, 3)
# S4 = ps.S('S4', 5, 3)
# S6 = ps.S('S6', 6, 3)
#
# Ra = ps.R('Ra', 4, 0, 100.0)
# Rb = ps.R('Rb', 5, 0, 100.0)
# Rc = ps.R('Rc', 6, 0, 100.0)
#
# cir.add_devices(Va, Vb, Vc, D1, D2, D3, D4, D5, D6, RL, Cf, Lf)
#
# sim = ps.Simulator(cir)
# sim.trans(0.0005, 0.1)
#
# sim.plot('tran',
#          ps.Voltage(1),
#          ps.Voltage(2),
#          ps.Voltage(3),
#          ps.Voltage(6, 5))


cir = ps.Circuit()
cir.title = "Saw Wave Stimulus Test and VCVS (E) Test"

Vs = ps.V('Vs', 1, 0, 3,
          ps.Pulse(v1=-10, v2=10, tr=0.1, tf=0.1, pw=0.0, per=0.2))

Ec = ps.E('Ec', 2, 0, 1, 0, 4, 10.0)
RL = ps.R('RL', 2, 0, 10.0)

cir.add_devices(Vs, Ec, RL)

sim = ps.Simulator(cir)

sim.trans(0.01, 1.0)

sim.plot('tran',
         ps.Voltage(1),
         ps.Voltage(2),
         ps.Current('Vs'),
         ps.Current('Ec'))

