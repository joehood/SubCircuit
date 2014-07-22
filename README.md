PySpyce
=======
Python Implementation of Berkeley SPICE3 Circuit Simulator

* [Download PySpyce (.zip)](https://github.com/josephmhood/PySpyce/zipball/master)
* [Download PySpyce (.tar.gz)](https://github.com/josephmhood/PySpyce/tarball/master)

PySpyce requires the [SciPy Stack](http://www.scipy.org/stackspec.html), which is available as part of several scientific Python distributions such as [iPython](http://ipython.org/) and [Enthought Canapy](https://www.enthought.com/products/canopy/). There are also SciPy Stack windows binaries available [here](http://www.lfd.uci.edu/~gohlke/pythonlibs/#scipy-stack).

PySpyce is a **_very new project_**, still in a proof-of-concept phase. The goal is to have a SPICE implementation in (mostly) native Python.
The benefits to a Python SPICE implementation are:
* Simple integration with other programs and Python libraries
* Modular, portable, and easily extensible
* Intuitive Python syntax and program structure

**Example plot:**
![Plot](/images/fig1.png)

**Example PyNetlist:**
![Netlist](/images/netlist1.png)

###Current Capabilities
* Basic circuit/subcircuit framework with high-level commands for building netlists
* Basic level-0 components (R, L, C, V, D), including source stimuli and models.
* Basic transient simulation and plotting capabilities

###Next Steps
* Complete level-0 versions of all atomic components and hide internal nodes
* Implement n-level subcircuit nesting and circuit expansion algorithm
* First-pass SPICE parser for importing SPICE *.cir files
