"""Voltage Scope Device."""

import pyspyce.sandbox as sb
import pyspyce.interfaces as inter
import pyspyce.stimuli as stim


class I(inter.MNADevice):
    """A SPICE Current source or current sensor."""

    def __init__(self, name, node1, node2,
                 value, resistance=0.0, **kwargs):

        """TODO
        """
        inter.MNADevice.__init__(self, name, 2)
        self.nodes = [node1, node2]
        self.node2port = {node1: 0, node2: 1}

        self.stimulus = None
        if isinstance(value, inter.Stimulus):
            self.stimulus = value
            self.stimulus.device = self
        else:
            self.value = value

        self.resistance = resistance

    def start(self, dt):

        g = 0.0
        if self.resistance > 0.0:
            g = 1.0 / self.resistance

        self.jac[0, 0] = g
        self.jac[0, 1] = -g
        self.jac[1, 0] = -g
        self.jac[1, 1] = g

        current = 0.0
        if self.stimulus:
            current = self.stimulus.start(dt)
        elif self.value:
            current = self.value

        self.bequiv[0] = current
        self.bequiv[1] = -current

    def step(self, dt, t):
        """Step the current source.
        """
        if self.stimulus:
            current = self.stimulus.step(dt, t)
        else:
            current = self.value

        self.bequiv[0] = current
        self.bequiv[1] = -current

