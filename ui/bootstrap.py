"""Environment bootstrap that must run before tkinter is imported.

Kept dependency-free (os/sys only) so it can run at package-import time from
``ui/__init__.py`` before customtkinter — and therefore tkinter — is loaded.
"""

import os
import sys


def configure_tcl_tk():
    """Point tkinter at the base interpreter's Tcl/Tk runtime on Windows.

    Windows venvs often can't locate the Tcl/Tk runtime (Tcl searches relative
    to ``.venv\\Scripts\\`` and never finds the base install's ``tcl`` folder),
    which makes tkinter fail to start. Guarded: only on Windows, only if not
    already configured, and only when the directories actually exist -- a no-op
    in healthy environments.
    """
    if sys.platform != "win32" or "TCL_LIBRARY" in os.environ:
        return

    tcl_root = os.path.join(sys.base_prefix, "tcl")
    tcl_lib = os.path.join(tcl_root, "tcl8.6")
    tk_lib = os.path.join(tcl_root, "tk8.6")
    if os.path.isdir(tcl_lib):
        os.environ["TCL_LIBRARY"] = tcl_lib
    if os.path.isdir(tk_lib):
        os.environ["TK_LIBRARY"] = tk_lib
