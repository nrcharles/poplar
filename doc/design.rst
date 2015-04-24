Design
======

Due to the open source and flexible nature of python, poplar can be easily extended and configured.  The core library provides small number of models that can be replaced or enhanced as needed.

Data Sources
^^^^^^^^^^^^
Weather data in these examples is managed by caelum from data hosted by the U.S. Department of Energy, Office of Energy Efficiency & Renewable Energy. This provides an interface to a global set of weather data.  The weather data comes from various sources. For more detail see the EERE description of weather sources_.

.. _sources: http://apps1.eere.energy.gov/buildings/energyplus/weatherdata_sources.cfm

Historical load data loads.annual comes from data reported by Bangladesh's Power Development Board (BPDB) in 2013 with missing data interpolated.


.. [Describe development of synthetic loads]


Solar
^^^^^

The local adjustment of historical weather data to a local site is accomplished via
models implemented in solpy.

.. autofunction:: solpy.irradiation.irradiation


.. autofunction:: solpy.irradiation.total_irr


.. autofunction:: solpy.irradiation.perez


Control
^^^^^^^

poplar uses a shared memory space environment to hold weather and global
variables.  Models are generally self contained but may pull parameters from this space.
When time is updated and a domain object is called, it initiates the market process that functions as a
market.

Models inherit a graph class that passes the system topology to every connected device object.
Every piece contains the image of the whole, every domain knows the topology of entire system.

.. [Describe how the Domain object inheritance is the crux of making this software work.]

.. [module interaction diagram]

.. [market description]

.. [energy value in market]
Determination of energy value is a per kWh value to determine energy destination
in selective energy dispatch.  It can correlate with kWh cost or another system.
In the current system, there should be no energy destinations that have equal
value.

..  How do I resolve equal value? is it important?


Storage in a domain must be valued similarly but less than desired end use and higher than less valued energy end uses.

.. graphviz:: market.gv

.. The inability to supply non-droopable loads is a shortfall and the inability to distibute
.. energy with curtailment penalties is a surplus.


.. literalinclude:: ../poplar/devices.py
   :pyobject: Gateway.transaction

.. [Domain accounting]
