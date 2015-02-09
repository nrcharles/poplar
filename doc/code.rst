Code
====


Devices
-------
The devices module is where all default devices reside. However the base
devices object is inherited by various other objects in other modules.

.. automodule:: devices
   :members:


power_io
^^^^^^^^

power_io is where the bulk of the IdealStorage logic happens.

.. literalinclude:: ../devices.py
   :pyobject: IdealStorage.power_io

Loads
-----

.. automodule:: loads
   :members:

Misc
----
Miscellaneous functions that don't obviously belong elsewhere.

.. automodule:: misc
   :members:

.. bibliography:: ../../../../bibtex/poplar.bib
    :cited:
