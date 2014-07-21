from pyspyce import *


title('Test RLC Netlist', '')
device('V1', V, 1, 0, 4, Sin(0.0, 1.0, 100.0))
device('R1', R, 1, 2, 1.0)
device('L1', L, 2, 3, 5, 0.01, ic=0.0)
device('C1', C, 3, 0, 0.001, ic=0.0)
trans(0.0005, 0.05)
plot('tran', Voltage(2), Voltage(3), Current('V1'))


'''
title('Test Generic Non-linear Device Netlist', '')
device('D1', GenericTwoPort, 1, 2, i=sympy.Expr(5.0e-9*(math.exp(v/25.85e-3) - 1.0)))
device('V1', V, 1, 0, 3, Sin(0.0, 1.0, 100.0))
device('R1', R, 2, 0, 1.0)
trans(0.0005, 0.05)
plot('tran', Voltage(2), Current('V1'))
'''