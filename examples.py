import pyspyce as ps


# def example1():
# circuit = ps.Circuit()
# circuit.title = 'Series RLC'
# circuit.add_device(ps.V, 1, 0, 4, ps.Sin(0.0, 1.0, 100.0))
# circuit.add_device('R1', ps.R, 1, 2, 1.0)
# circuit.add_device('L1', ps.L, 2, 3, 5, 0.01, ic=0.0)
#   circuit.add_device('C1', ps.C, 3, 0, 0.001, ic=0.0)
#
#   simulator = ps.Simulator(circuit)
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
# circuit.add_device(ps.V('V1', 1, 0, 5, ps.Sin(0.0, 10.0, 100.0)))
# circuit.add_device(ps.R('R1', 1, 2, 0.01))
# circuit.add_device(ps.L('L1', 2, 0, 6, 0.001))
# circuit.add_device(ps.L('L2', 3, 0, 7, 0.002))
# circuit.add_device(ps.K('K1', 'L1', 'L2', 0.999))
# circuit.add_device(ps.R('R2', 3, 4, 10.0))
# circuit.add_device(ps.V('VS',  0, 4, 8, 0.0))
# simulator = ps.Simulator(circuit)
# simulator.trans(0.0001, 0.05)
# simulator.plot('tran', ps.Voltage(1), ps.Voltage(3), ps.Current('V1'), ps.Current('VS'))

circuit = ps.Circuit()
circuit.title = 'Diode Test'
circuit.add_device(ps.V('V1', 1, 0, 2, ps.Pwl([0.0, 0.0], [1.0, 0.0], [1.01, 0.6], [2.0, 0.6], [2.01, 0.0])))
circuit.add_device(ps.D('D1', 1, 0, 'Diode1'))
circuit.add_model(ps.DMod('Diode1', IS=1.0e-9))
simulator = ps.Simulator(circuit)
simulator.trans(0.02, 4.0)
simulator.plot('tran', ps.Voltage(1), ps.Current('V1'))