"""Q (BJT NPN and PNP) device models and interfaces."""

import subcircuit.interfaces as inter
import subcircuit.sandbox as sb
import math


class Q(inter.MNADevice):
    """Bipolar Junction Transistor (BJT)"""

    def __init__(self, nodes, model=None, area=None, off=True, ic=None,
                 temp=None, **parameters):

        """Creates a new Q (BJT) device.
        :param nodes: sequence of node connections: (NC, NB, NE [,NC])
        :param model: optional Q model
        :param area: surface area
        :param off: intially in off condition
        :param IC: intial voltage condition
        :param temp: operating temperature
        :param parameters: optional parameters (override model params)
        :return: new Q device

        base currents:

        ibf = (ifs / betaf) * (math.exp(vbe / vt) - 1)
        ibr = (irs / betar) * (math.exp(vbc / vt) - 1)

        small-signal conductances:

        gpif = (ifs / betaf) * math.exp(vbe / vt) / vt
        gpir = (irs / betar) * math.exp(vbc / vt) / vt
        gmf = ifs * math.exp(vbe / vt) / vt = betaf * gpif
        gmr = irs * math.exp(vbc / vt) / vt = betar * gpir

        from general bias current formula:

        ibfeq = ibf(vbe) - gpif * vbe
        ibreq = ibr(vbc) - gpir * vbc
        iceq = ic(vbe. vbc) - gmf * vbe + gmr * vbc - go * vbe

        NPN:

        equiv large-signal model:

                   o C
                   |
               |---'
        B o----|
               |-->.
                   |
                   o E
                            ibreq
                             ,-.
                        .---(-->)---.
                        |    `-'    |
                        |           |
                        |   gpir    |
        B o----+--------+---/\/\/---+----------+--------+-------+----o C
               |        |           |          |        |       |
               <       ,|.         /|\        / \       <      ,|.
               < gpif ( v )ibreq  ( v )gmf*  ( ^ )gmr*  < go  ( v ) iceq
               <       `-'         \ / vbe    \|/ vbc   <      `-'
               |        |           |          |        |       |
        E o----+--------+-----------+----------+--------+-------'


        PNP:
                   o E
                   |
               |<--'
        B o----|
               |---.
                   |
                   o C
                            ibreq
                             ,-.
                        .---(<--)---.
                        |    `-'    |
                        |           |
                        |   gpir    |
        B o----+--------+---/\/\/---+----------+--------+-------+----o C
               |        |           |          |        |       |
               <       ,-.         / \        /|\       <      ,-.
               < gpif ( ^ )ibreq  ( ^ )gmf*  ( v )gmr*  < go  ( ^ ) iceq
               <       `|'         \|/ vbe    \ / vbc   <      `|'
               |        |           |          |        |       |
        E o----+--------+-----------+----------+--------+-------'

        """

        inter.MNADevice.__init__(self, nodes, 0, **parameters)

        self.model = model
        self.area = area
        self.off = off
        self.ic = ic
        self.temp = temp

        self.pc = 0
        self.pb = 1
        self.pe = 2

    def connect(self):
        nc, nb, ne = self.nodes
        self.port2node = {self.pc: self.get_node_index(nc),
                          self.pb: self.get_node_index(nb),
                          self.pe: self.get_node_index(ne)}

    def start(self, dt):

        # set defaults:

        self.is_ = 1.0e-15
        self.bf = 100
        self.nf = 1.0
        self.vaf = 200.0
        self.ikf = 0.01
        self.ise = 1.0e-13
        self.ne = 2.0
        self.br = 0.1
        self.nr = 1.0
        self.var = 200.0
        self.ikr = 0.01
        self.isc = 1.0e-13
        self.nc = 1.5
        self.rb = 100.0
        self.irb = 0.1
        self.rbm = 10.0
        self.re = 0.001
        self.rc = 0.001
        self.cje = 2.0e-12
        self.vje = 0.6
        self.mje = 0.33
        self.tf = 0.1e-9
        self.xtf = 0.0
        self.vtf = float('inf')
        self.itf = 0.0
        self.ptf = 0.0
        self.cjc = 2.0e-9
        self.vjc = 0.5
        self.mjc = 0.5
        self.xcjc = 1.0
        self.tr = 10.0e-12
        self.cjs = 2.0e-9
        self.vjs = 0.75
        self.mjs = 0.5
        self.xtb = 0.0
        self.eg = 1.11
        self.xti = 3.0
        self.kf = 0.0
        self.af = 1.0
        self.fc = 0.5
        self.tnom = 50.0

    def minor_step(self, dt, t, k):

        # get params (that are currently supported !):
        ifs = self.is_
        irs = self.is_
        is_ = self.is_
        betaf = self.bf
        betar = self.br
        vt = 25.85e-3
        go = 1.0 / self.re

        # get voltage estimates from the latest solution:
        vbe = self.get_across(self.pb, self.pe)
        vbc = self.get_across(self.pb, self.pc)

        # update the current estimates:
        ibf = (ifs / betaf) * (math.exp(vbe / vt) - 1)
        ibr = (irs / betar) * (math.exp(vbc / vt) - 1)
        ic = (is_ * (math.exp(vbe / vt) - math.exp(vbc / vt)) -
             is_ / betar * (math.exp(vbc / vt) - 1))

        # update conductance estimates:
        gpif = (ifs / betaf) * math.exp(vbe / vt) / vt
        gpir = (irs / betar) * math.exp(vbc / vt) / vt
        gmf = betaf * gpif
        gmr = betar * gpir

        # calculate the equiv injections:
        ibfeq = ibf - gpif * vbe
        ibreq = ibr - gpir * vbc
        iceq = ic - gmf * vbe + gmr * vbc - go * vbe

        """

                    gpir
        B o----+----/\/\/---+----o C
               |            |
               <            <
               < gpif       < go
               <            <
               |            |
        E o----+------------'

                   ibreq
                     ,-.
        B o-----+---(-->)---+----------+----------+----o C
                |    `-'    |          |          |
               ,|.         /|\        / \        ,|.
              ( v )ibreq  ( v )gmf*  ( ^ )gmr*  ( v ) iceq
               `-'         \ / vbe    \|/ vbc    `-'
                |           |          |          |
        E o-----+-----------+----------+----------'
        """

        self.jac[self.pc, self.pc] = gpir + go
        self.jac[self.pc, self.pb] = -gpir
        self.jac[self.pc, self.pe] = -go
        self.jac[self.pb, self.pc] = -gpir
        self.jac[self.pb, self.pb] = gpir + gpif
        self.jac[self.pb, self.pe] = -gpif
        self.jac[self.pe, self.pc] = -go
        self.jac[self.pe, self.pb] = -gpif
        self.jac[self.pe, self.pe] = gpif + gpir

        self.bequiv[self.pc] = iceq + gmf * vbe - gmr * vbc - ibreq
        self.bequiv[self.pb] = ibfeq + ibreq
        self.bequiv[self.pe] = gmr * vbc -ibreq - gmf * vbe - iceq


class QNPNBlock(sb.Block):
    friendly_name = "BJT (NPN)"
    family = "Semiconductors"
    label = "Q"
    engine = Q

    def __init__(self, name):
        sb.Block.__init__(self, name, Q)

        """
                   o C
                   |
               |---'
        B o----|     NPN
               |-->.
                   |
                   o E

        """

        # ports NPN:
        self.ports['collector'] = sb.Port(self, 0, (80, 0))
        self.ports['base'] = sb.Port(self, 1, (0, 40))
        self.ports['emitter'] = sb.Port(self, 2, (80, 80))

        # properties:

        # symbol:
        self.lines.append(((80, 0), (40, 25)))
        self.lines.append(((0, 40), (40, 40)))
        self.lines.append(((80, 80), (40, 55)))
        self.lines.append(((40, 10), (40, 70)))

        self.lines.append(((63, 80), (80, 80), (73, 65)))

    def get_engine(self, nodes):
        return Q(nodes)