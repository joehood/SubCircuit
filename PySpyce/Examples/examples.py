
import sys
sys.path.append('./')
from pyspyce import *


def example1():
  title('Series RLC', '')
  device('V1', V, 1, 0, 4, Sin(0.0, 1.0, 100.0))
  device('R1', R, 1, 2, 1.0)
  device('L1', L, 2, 3, 5, 0.01, ic=0.0)
  device('C1', C, 3, 0, 0.001, ic=0.0)
  trans(0.0005, 0.05)
  plot('tran', Voltage(2), Voltage(3), Current('V1'))

def example2():
  title('Half-wave Rectifier', '')
  device('V1', V, 1, 0, 4, Sin(0.0, 1.0, 100.0))
  device('R1', R, 1, 2, 0.2)
  device('D1', D, 2, 3, 'Diode1')
  device('R2', R, 3, 0, 2.0)
  device('C1', C, 3, 0, 0.01)
  model('Diode1', DMOD, IS=1.0e-9)
  trans(0.0002, 0.05)
  plot('tran', Voltage(1), Voltage(3))

def example3():
  title('Full-wave Rectifier', '')
  device('V1', V, 2, 3, 6, Sin(0.0, 10.0, 100.0))
  device('D1', D, 2, 1, 'Diode1')
  device('D2', D, 3, 1, 'Diode1')
  device('D3', D, 4, 2, 'Diode1')
  device('D4', D, 4, 3, 'Diode1')
  device('R1', R, 5, 4, 10.0)
  device('R2', R, 4, 0, 1000.0)
  device('C1', C, 5, 4, 0.002)
  device('L1', L, 1, 5, 7, 0.0001)
  model('Diode1', DMod, IS=1.0e-9)
  trans(0.0001, 0.04)
  plot('tran', Voltage(2, 3), Voltage(5, 4), Current('V1'))

def example4():
  '''
         R1
   1.---VVV---.2     3.-------.
    |         |<- K ->|       >
   .'.        )       (       >R2
  ( V )5     6)L1   L2(       >
   '.'        )       (       | 4
    |         |       |     (VS )
    '---------'0     0'-------'
  '''
  title('Mutual Inductance Test')
  device('V1', V, 1, 0, 5, Sin(0.0, 10.0, 100.0))
  device('R1', R, 1, 2, 0.01)
  device('L1', L, 2, 0, 6, 0.001)
  device('L2', L, 3, 0, 7, 0.002)
  device('K1', K, 'L1', 'L2', 1.1)
  device('R2', R, 3, 4, 10.0)
  device('VS', V, 0, 4, 8, 0.0)
  trans(0.0001, 0.05)
  plot('tran', Voltage(1), Voltage(3), Current('V1'), Current('VS'))



#example1()
#example2()
#example3()
example4()




