Code
====

Devices
-------
The devices module is where all default devices reside. However the base
devices object is inherited by various other objects in other modules.

.. automodule:: devices
   :members:

Controllers
-----------

.. automodule:: controllers
   :members:

Sources
-------

.. automodule:: sources
   :members:

Loads
-----

.. automodule:: loads
   :members:


Storage
-------

.. automodule:: storage
   :members:

power_io
^^^^^^^^

power_io is where the bulk of the IdealStorage logic happens.

.. literalinclude:: ../storage.py
   :pyobject: IdealStorage.power_io

Misc
----
Miscellaneous functions that don't obviously belong elsewhere.

.. automodule:: misc
   :members:

