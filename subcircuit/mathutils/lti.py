
import math
import numpy as np
import numpy.linalg as la
import matplotlib.pyplot as plt
import sympy
from sympy.parsing.sympy_parser import parse_expr


class LTISystem(object):
    def __init__(self):
        pass

    def reset(self, dt):
        raise NotImplementedError()

    def step(self, u, dt, t):
        raise NotImplementedError()

    def rollback(self, dt, t):
        raise NotImplementedError()


class StateSpace(LTISystem):

    def __init__(self, a, b, c, d=None, xo=None):

        """TODO
        :param a:
        :param b:
        :param c:
        :param d:
        :param xo:
        :return:
        """

        LTISystem.__init__(self)

        # grab arguments:
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.xo = xo

        # get system size:
        self.n, x = a.shape
        x, self.m = b.shape
        self.l, x = c.shape

        if not self.d:
            self.d = np.zeros((self.m, self.l))

        if not self.xo:
            self.xo = np.zeros((self.n, 1))

        self.x = self.xo[:, :]
        self.xh = self.xo[:, :]

        self.u = np.zeros((self.n, 1))
        self.y = np.zeros((self.m, 1))
        self.y = None

    def reset(self, dt):

        self.x = self.xo[:, :]
        self.xh = self.xo[:, :]
        self.u = np.zeros((self.n, 1))

    def step(self, u, dt, t):

        self.u = u

        dx = self.a.dot(self.x) + self.b.dot(u)
        self.x = self.x + dx.dot(dt)
        self.y = self.c.dot(self.x) + self.d.dot(u)

        self.xh = self.x[:, :]

        return self.y

    def rollback(self, dt, t):

        pass


class TransferFunction(LTISystem):
    def __init__(self, equation):
        LTISystem.__init__(self)

        self.is_gain = False

        self.equation = equation
        self.ss = None
        self.reset(0.0)

    def reset(self, dt):

        equ = parse_expr(self.equation)

        num, den = equ.as_numer_denom()

        self.is_gain = False

        if str(den).find("s") >= 0:  # if s domain expr:
            a = self.expr2poly(den)
            self.is_gain = False
        else:
            a = [eval(str(den))]

        if str(num).find("s") >= 0:  # if s domain expr:
            b = self.expr2poly(num)
            self.is_gain = False
        else:
            b = [eval(str(num))]

        if self.is_gain:
            A = np.zeros((1, 1))
            B = np.zeros((1, 1))
            C = np.zeros((1, 1))
            D = np.zeros((1, 1))

        else:
            n = len(a)

            # now convert tf to ss (CCF):

            n = len(a)
            ao = a[0]

            b2 = np.zeros(n)
            b2[(n - len(b)):] = b
            bo = b2[0]
            b = b2[:]

            # truncate:

            a = a[1:]
            b = b[1:]
            n -= 1

            # normalize:

            for i in range(n):
                a[i] /= ao
                b[i] /= ao

            A = np.zeros((n, n))
            B = np.zeros((n, 1))
            C = np.zeros((1, n))
            D = np.zeros((1, 1))

            # a matrix and c vector:

            for i in range(n):
                for j in range(n):
                    if j == i+1:
                            A[i, j] = 1.0
                    elif i == n-1:
                        A[i, j] = -a[j]
                C[0, i] = b[-(i+1)] - a[-(i+1)] * bo

            # b vector:
            B[-1, 0] = 1.0

            # d matrix:
            D[0, 0] = bo

        self.ss = StateSpace(A, B, C, D)

    def step(self, u, dt, t):
        return self.ss.step(u, dt, t)

    def rollback(self, dt, t):
        pass

    @staticmethod
    def expr2poly(expr, n=None):

        poly = sympy.Poly(expr)
        coeffs = poly.all_coeffs()

        return coeffs


if __name__ == "__main__":

    A = np.mat([[0, 1], [-1, -1]])
    B = np.mat([[0], [1]])
    C = np.mat([[1, 0]])

    ss = StateSpace(A, B, C)

    u = 10.0

    tp = np.linspace(0.0, 1.0, 50)
    to = 0.0

    xp = np.zeros((len(tp)))

    for i, t in enumerate(tp):
        dt = t - to
        y = ss.step(u, dt, t)
        xp[i] = y
        print(y)

    plt.plot(tp, xp)
    plt.show()