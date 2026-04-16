"""Make the `scripts` directory a Python package.

The test suite imports modules using ``from scripts import train_models`` and
``from scripts import sweep_hyperparameters``. Adding an empty ``__init__`` file
allows those imports to resolve correctly without altering the existing module
structure.
"""

