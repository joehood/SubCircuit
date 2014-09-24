"""Stimuli definitions for independant sources.

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


class Pulse(inter.Stimulus):
    def __init__(self, v1, v2, td=0.0, tr=None, tf=None, pw=None, per=None):
        """
        General form:

             PULSE(V1 V2 TD TR TF PW PER)

        Examples:

             VIN 3 0 PULSE(-1 1 2NS 2NS 2NS 50NS 100NS)

        parameter	default value	units
        V1 (initial value)	 	V or A
        V2 (pulsed value)	 	V or A
        TD (delay time)	0.0	s
        TR (rise time)	TSTEP	s
        TF (fall time)	TSTEP	s
        PW (pulse width)	TSTOP	s
        PER (period)	TSTOP	seconds

        A single pulse so specified is described by the following table:

        time        value
        -----------------
        0           V1
        TD          V1
        TD+TR       V2
        TD+TR+PW    V2
        TD+TR+PW+TF V1
        TSTOP       V1

        Intermediate points are determined by linear interpolation.
        """
        self.v1 = v1
        self.v2 = v2
        self.td = td
        self.tr = tr
        self.tf = tf
        self.pw = pw
        self.per = per
        self.device = None

    def start(self, dt):
        if self.tr is None:
            self.tr = dt
        if self.tf is None:
            self.tf = dt
        if self.pw is None:
            self.pw = dt
        if self.per is None:
            self.per = float('inf')
        return self.v1

    def step(self, dt, t):
        t %= self.per
        if (self.td + self.tr) <= t < (self.td + self.tr + self.pw):
            return self.v2
        elif self.td <= t < (self.td + self.tr):
            return self.v1 + (self.v2 - self.v1) * (t - self.td) / self.tr
        elif ((self.td + self.tr + self.pw) <= t <
              (self.td + self.tr + self.pw + self.tf)):
            return (self.v2 + (self.v1 - self.v2) *
                    (t - (self.td + self.tr + self.pw)) / self.tf)
        else:
            return self.v1

    def __str__(self):
        s = "Pulse({0}, {1}, {2}, {3}, {4}, {5}, {6})".format(self.v1, self.v2,
                                                         self.td, self.tr,
                                                         self.tf, self.pw,
                                                         self.per)
        return s

    def __repr__(self):
        return str(self)


class Sin(inter.Stimulus):
    """Models a sin wave stimulus for independent sources."""

    def __init__(self, vo=0.0, va=1.0, freq=1.0, td=0.0, theta=0.0, phi=0.0):
        """
        General form:

             SIN(VO VA FREQ TD THETA)

        Examples:

             VIN 3 0 SIN(0 1 100MEG 1NS 1E10)

        parameters	default value	units
        VO (offset)	 	V or A
        VA (amplitude)	 	V or A
        FREQ (frequency)	1/TSTOP	Hz
        TD (delay)	0.0	s
        THETA (damping factor)	0.0	s-1

        The shape of the waveform is described by the following table:

        time, t	value
        0 to TD	VO
        TD to TSTOP	VO+VA.exp[-(t-TD)/THETA].sin[2pi.FREQ.(t+TD)]
        """
        self.vo = vo
        self.va = va
        self.freq = freq
        self.td = td
        self.theta = theta
        self.phi = phi
        self.device = None

    def start(self, dt):
        """Sets up the pulse stimulus and returns the initial output."""
        return self.step(dt, 0.0)

    def step(self, dt, t):
        """Update and return the stimulus value at the current time."""
        if t < self.td:
            return 0.0
        elif self.theta:
            return (self.vo + self.va * math.exp(-(t + self.td) / self.theta) *
                    math.sin(2.0 * math.pi * self.freq
                             * (t + self.td) + self.phi))
        else:
            return self.vo + self.va * math.sin(
                2.0 * math.pi * self.freq * (t + self.td) + self.phi)

    def __str__(self):
        s = "Sin({0}, {1}, {2}, {3}, {4}, {5})".format(self.vo, self.va,
                                                       self.freq, self.td,
                                                       self.theta, self.phi)
        return s

    def __repr__(self):
        return str(self)


class Exp(inter.Stimulus):
    """Generates a SPICE EXP stimulus for independant sources."""

    def __init__(self, v1, v2, td1=0.0, tau1=None, td2=None, tau2=None):
        """
        Define a pulse stimulus.
        :param v1: initial value (V or A)
        :param v2: pulsed value (V or A)
        :param td1: rise time delay, default=0.0 (s)
        :param tau1: rise time constant default=None (will be set to timestep) (s)
        :param td2: fall delay time, default=None (will be set to td1 + timestep) (s)
        :param tau2: fall time constant, default=None (will be set to timestep) (s)
        :return: None
        """
        self.v1 = v1
        self.v2 = v2
        self.td1 = td1
        self.tau1 = tau1
        self.td2 = td2
        self.tau2 = tau2

    def start(self, dt):
        """Initialize the Exp output at time 0s."""
        if not self.tau1:
            self.tau1 = dt
        if not self.td2:
            self.td2 = self.td1 + dt
        if not self.tau2:
            self.tau2 = dt
        return self.step(dt, 0.0)

    def step(self, dt, t):
        """Update and return the current value of the Exp stimulus"""
        if 0.0 >= t < self.td1:
            return self.v1
        elif self.td1 <= t < self.td1:
            return self.v1 + (self.v2 - self.v2) * (
                   1.0 - math.exp(-(t - self.td1) / self.tau1))
        else:
            return (1.0 + (self.v2 - self.v1)
                    * (1.0 - math.exp(-(t - self.td1) / self.tau1))
                    + (self.v1 - self.v2) * (
                    1.0 - math.exp(-(t - self.td2) / self.tau2)))

    def __str__(self):
        s = "Exp({0}, {1}, {2}, {3}, {4}, {5})".format(self.v1, self.v2,
                                                       self.td1, self.tau1,
                                                       self.td2, self.tau2)
        return s

    def __repr__(self):
        return str(self)


class Pwl(inter.Stimulus):
    """TODO Doc"""
    def __init__(self, *time_voltage_pairs):
        self.xp = []
        self.yp = []
        for time, value in time_voltage_pairs:
            try:
                self.xp.append(float(time))
                self.yp.append(float(value))
            except ValueError as e:
                pass
            pass

    def start(self, dt):
        pass

    def step(self, dt, t):
        x = self.device.get_time()
        return self._interp_(x)

    def _interp_(self, x):
        if x <= self.xp[0]:
            return self.yp[0]
        elif x >= self.xp[-1]:
            return self.yp[-1]
        else:
            itr = 1
            while x > self.xp[itr] and itr < (len(self.xp) - 1):
                itr += 1
            x0, y0 = self.xp[itr - 1], self.yp[itr - 1]
            x1, y1 = self.xp[itr], self.yp[itr]
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)

    def __str__(self):
        p = ""
        for x, y in zip(self.xp, self.yp):
            p += "({0}, {1}),".format(x, y)
        s = "Pwl({0})".format(p.strip(","))
        return s

    def __repr__(self):
        return str(self)



class Sffm(inter.Stimulus):
    def __init__(self, vo, va, fc, md1, fs):
        pass  # todo

    def start(self, dt):
        pass

    def step(self, dt, t):
        pass
