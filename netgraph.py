from __future__ import print_function

r"""

Port(subnet, superport, subport, index)

example:

v 1 0 10
r 1 2 5
x input output 'x' (nodes) (ports: 1, 2)


subckt x 1 2
c 1 3 10   (nodes) (ports: 0, 1) (replace these nodes with x ports)
l 3 2 20   (nodes) (ports: 0, 1) (replace these nodes with x ports)

     (n,0)       (n,1)       (n,2)       (v,2)       (x,2)       (l,2)
      / \         / \         / \          |           |           |
     /   \       /   \       /   \         |           |           |
  (v,0) (x,1) (v,1) (r,0) (r,1) (x,0)    (v,2)       (x,2)       (l,2)
          |                       |                   / \          |
          |                       |                  /   \         |
        (c,1)                   (l,0)             (l,1) (c,0)    (l,2)


             (n)
            / | \
           /  |  \
         (v) (r) (x)
                 / \
                /   \
              (c)   (l)

"""
import copy
import numpy.linalg as la
import numpy as np


class Net(object):
    def __init__(self, supernet=None, atomic=False):
        self.supernet = supernet
        self.atomic = atomic
        self.subnets = {}
        self.ports = {}
        self.params = {}
        self.nodes = None

    def map_nodes(self, supernodes):
        for netname, net in self.subnets.items():
            for portname, port in net.ports.items():
                pass

    def jstamp(self, stamp):
        pass

    def bstamp(self, stamp):
        pass


class Circuit(object):
    def __init__(self):
        self.root = Net()

    def add_device(self, name, device):
        pass
    def solve(self):
        self.jstamp()
        self.bstamp()
        # x = la.solve(self.jac[1:, 1:], self.beq[1:])
        # return x


class Subckt(Net):
    def __init__(self, parent):
        Net.__init__(self, supernet=parent)

    def add_device(self, name, device):
        if not name in self.subnets:
            self.subnets[name] = device


class Device(Net):
    def __init_(self, parent):
        Net.__init__(self, supernet=parent, atomic=True)

    def jstamp(self):
        raise NotImplementedError()

    def bstamp(self):
        raise NotImplementedError()


# Devices:

class V(Device):
    def __init__(self, parent, npos, nneg, value=0.0):
        Device.__init__(parent)
        self.value = value
        self.nodes[npos] = 0
        self.nodes[nneg] = 1
        self.nodes['IN'] = 2
        self.jac = np.zeros((3, 3))
        self.beq = np.zeros((3, 1))

    def jstamp(self):
        self.jac[0, 2] = 1.0
        self.jac[1, 2] = -1.0
        self.jac[2, 0] = 1.0
        self.jac[2, 1] = -1.0

    def bstamp(self):
        self.beq[2] = self.value


class R(Device):
    def __init__(self, parent, npos, nneg, value=0.0):
        Device.__init__(parent)
        self.value = value
        self.nodes[npos] = 0
        self.nodes[nneg] = 1
        self.jac = np.zeros((2, 2))
        self.beq = np.zeros((2, 1))

    def jstamp(self):
        self.jac[0, 0] = 1.0 / self.value
        self.jac[0, 1] = -1.0 / self.value
        self.jac[1, 0] = -1.0 / self.value
        self.jac[1, 1] = 1.0 / self.value

    def bstamp(self):
        pass


class Rdiv(Subckt):
    def __init__(self, parent, npos, nneg, r1=0.0, r2=0.0):
        Subckt.__init__(self, parent)
        self.nodes[npos] = 0
        self.nodes[nneg] = 1
        self.nodes['IN'] = 2
        self.subnets['R1'] = R(self, 0, 2, r1)
        self.subnets['R2'] = R(self, 2, 1, r2)


# Test script:

if __name__ == '__main__':

    cir = Circuit(0, 1, 2)
    V(cir, 1, 0, 100.0)
    R(cir, 1, 2, 10.0)
    Rdiv(cir, 2, 0, r1=10.0, r2=20.0)

    cir.solve()

