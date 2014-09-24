"""D (Diode) device.

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

import math

import subcircuit.interfaces as inter
import subcircuit.sandbox as sb


class D(inter.MNADevice):
    """Represents a SPICE Diode device."""

    def __init__(self, nodes, model=None, area=None, off=None,
                 ic=None, temp=None, **parameters):
        """
        General form:

             DXXXXXXX N+ N- MNAME <AREA> <OFF> <IC=VD> <TEMP=T>

        Examples:

             DBRIDGE 2 10 DIODE1
             DCLMP 3 7 DMOD 3.0 IC=0.2

        N+ and N- are the positive and negative nodes, respectively. MNAME is the model name,
        AREA is the area factor, and OFF indicates an (optional) starting condition on the
        device for dc analysis. If the area factor is omitted, a value of 1.0 is assumed. The
        (optional) initial condition specification using IC=VD is intended for use with the
        UIC option on the .TRAN control line, when a transient analysis is desired starting
        from other than the quiescent operating point. The (optional) TEMP value is the
        temperature at which this device is to operate, and overrides the temperature
        specification on the .OPTION control line.
        """
        inter.MNADevice.__init__(self, nodes, 0, **parameters)
        self.mname = model
        self.area = area
        self.off = off
        self.ic = ic
        self.temp = temp

        # default model parameters:
        self.is_ = 1.0e-14
        self.rs = 0.0
        self.n = 1.0
        self.tt = 0.0
        self.cjo = 0.0
        self.vj = 1.0
        self.m = 0.5
        self.eg = 1.11
        self.xti = 3.0
        self.kf = 0.0
        self.af = 1.0
        self.fc = 0.5
        self.bv = float('inf')
        self.ibv = 1.0e-3
        self.tnom = 27.0
        self.model = None

    def connect(self):
        nplus, nminus = self.nodes
        self.port2node = {0: self.get_node_index(nplus),
                          1: self.get_node_index(nminus)}

    def start(self, dt):

        # transfer model params from model to member variables (__dict__)
        # if one is asscociated with this device:

        if self.model:
            for key in self.model.parameters:
                if key in self.__dict__:
                    self.__dict__[key] = self.model.parameters[key]

        # now override with any passed-in keyword args:

        if self.parameters:
            for key in self.parameters:
                if key in self.__dict__:
                    self.__dict__[key] = self.parameters[key]

    def minor_step(self, dt, t, k):
        vt = 25.85e-3
        v = self.get_across(0, 1)
        v = min(v, 0.8)
        geq = self.is_ / vt * math.exp(v / vt)
        ieq = self.is_ * (math.exp(v / vt) - 1.0)
        beq = ieq - geq * v
        self.jac[0, 0] = geq
        self.jac[0, 1] = -geq
        self.jac[1, 0] = -geq
        self.jac[1, 1] = geq
        self.bequiv[0] = -beq
        self.bequiv[1] = beq


class DBlock(sb.Block):
    friendly_name = "Diode"
    family = "Semiconductors"
    label = "D"
    engine = D

    symbol = sb.Symbol()
    # leads:
    symbol.lines.append(((60, 0), (60, 37)))
    symbol.lines.append(((60, 63), (60, 100)))

    # diode symbol:
    symbol.lines.append(((60, 37), (42, 63), (78, 63), (60, 37)))
    symbol.lines.append(((42, 37), (78, 37)))

    def __init__(self, name):
        sb.Block.__init__(self, name, D)

        # ports:
        self.ports['anode'] = sb.Port(self, 0, (60, 100))
        self.ports['cathode'] = sb.Port(self, 1, (60, 0))

        # properties:
        self.properties['Isat (I)'] = 1.0E-9
        self.properties['Vt (V)'] = 25.85e-3

    def get_engine(self, nodes):
        return D(nodes)



