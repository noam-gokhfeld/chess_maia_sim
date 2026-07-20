"""Desktop UI package for the Maia chess game simulator.

Importing this package runs the Windows Tcl/Tk bootstrap *before* any submodule
imports customtkinter/tkinter. Python executes this ``__init__`` before the body
of any ``ui.*`` submodule, so ``from ui.app import run`` is enough to guarantee
the fix is applied in time. Nothing imported here may pull in tkinter.
"""

from ui import bootstrap

bootstrap.configure_tcl_tk()
