"""V (independant voltage source) device.

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
import subcircuit.stimuli as stim


class SignalSource(inter.SignalDevice):
    def __init__(self, nodes, value, **parameters):
        inter.SignalDevice.__init__(self, nodes, **parameters)

        # determine type of value provided:
        if isinstance(value, inter.Stimulus):
            self.stimulus = value
            self.stimulus.device = self
        elif isinstance(value, float) or isinstance(value, int):
            self.stimulus = None
            self.value = float(value)

        self.value = value

    def connect(self):
        output = self.nodes[0]
        self.port2node = {0: self.get_node_index(output)}

    def update(self):
        pass

    def start(self, dt):
        if self.stimulus:
            output = self.stimulus.start(dt)
        else:
            output = self.value
        self.set_port_value(0, output)

    def step(self, dt, t):
        if self.stimulus:
            output = self.stimulus.step(dt, t)
        else:
            output = self.value
        self.set_port_value(0, output)

    def post_step(self, dt, t):
        pass


class ConstantBlock(sb.Block):
    """Schematic graphical interface for State Space device."""
    friendly_name = "Constant Source"
    family = "Signal Sources"
    label = "Const"
    engine = SignalSource

    symbol = sb.Symbol()

    # lead:
    symbol.lines.append(((80, 60), (100, 60)))

    # circle
    symbol.circles.append((60, 60, 20))

    # lines:
    symbol.lines.append(((48, 60), (72, 60)))

    def __init__(self, name):
        sb.Block.__init__(self, name, None, is_signal_device=True)

        self.ports["output"] = sb.Port(self, 0, (100, 60),
                                       sb.PortDirection.OUT,
                                       block_edge=sb.Alignment.E)

        # properties:
        self.properties['Constant Value'] = 1.0

    def design_update(self):
        pass

    def end(self):
        pass

    def get_engine(self, nodes):

        const = self.properties['Constant Value']

        return SignalSource(nodes, const)


class SineBlock(sb.Block):
    """Schematic graphical interface for State Space device."""
    friendly_name = "Sine Source"
    family = "Signal Sources"
    label = "Sine"
    engine = SignalSource

    symbol = sb.Symbol()

    # leads:
    symbol.lines.append(((90, 60), (120, 60)))

    # circle
    symbol.circles.append((60, 60, 30))

    # sine:
    a1 = math.pi
    a2 = 0.0
    symbol.arcs.append((50, 60, 10, a1, a2, True))
    symbol.arcs.append((70, 60, 10, -a1, -a2, False))

    def __init__(self, name):
        sb.Block.__init__(self, name, None, is_signal_device=True)

        self.ports["output"] = sb.Port(self, 0, (120, 60),
                                       sb.PortDirection.OUT,
                                       block_edge=sb.Alignment.E)

        # properties:
        self.properties['Offset'] = 0.0
        self.properties['Amplitude'] = 1.0
        self.properties['Frequency (Hz)'] = 60.0
        self.properties['Delay (s)'] = 0.0
        self.properties['Damping factor (1/s)'] = 0.0
        self.properties['Phase (rad)'] = 0.0

    def design_update(self):
        pass

    def end(self):
        pass

    def get_engine(self, nodes):

        vo = self.properties['Offset']
        va = self.properties['Amplitude']
        freq = self.properties['Frequency (Hz)']
        td = self.properties['Delay (s)']
        theta = self.properties['Damping factor (1/s)']
        phi = self.properties['Phase (rad)']

        sine = stim.Sin(vo, va, freq, td, theta, phi)

        return SignalSource(nodes, sine)


class PulseBlock(sb.Block):
    """Schematic graphical interface for State Space device."""
    friendly_name = "Pulse Source"
    family = "Signal Sources"
    label = "Pulse"
    engine = SignalSource

    symbol = sb.Symbol()

    # leads:
    symbol.lines.append(((90, 60), (120, 60)))

    # circle
    symbol.circles.append((60, 60, 30))

    # pulse:
    symbol.lines.append(((40, 65), (53, 65), (53, 55),
                       (67, 55), (67, 65), (80, 65)))

    def __init__(self, name):
        sb.Block.__init__(self, name, None, is_signal_device=True)

        self.ports["output"] = sb.Port(self, 0, (120, 60),
                                       sb.PortDirection.OUT,
                                       block_edge=sb.Alignment.E)

        # properties:
        self.properties['Level 1'] = 0.0
        self.properties['Level 2'] = 1.0
        self.properties['Delay (s)'] = 0.0
        self.properties['Rise Time (s)'] = 0.0
        self.properties['Fall Time (s)'] = 0.0
        self.properties['Width (s)'] = 0.01
        self.properties['Period (s)'] = 0.02

    def design_update(self):
        pass

    def end(self):
        pass

    def get_engine(self, nodes):

        v1 = self.properties['Level 1']
        v2 = self.properties['Level 2']
        td = self.properties['Delay (s)']
        tr = self.properties['Rise Time (s)']
        tf = self.properties['Fall Time (s)']
        pw = self.properties['Width (s)']
        per = self.properties['Period (s)']

        pulse = stim.Pulse(v1, v2, td, tr, tf, pw, per)

        return SignalSource(nodes, pulse)