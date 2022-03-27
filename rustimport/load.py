import logging
import sys
from contextlib import contextmanager

from rustimport import settings

logger = logging.getLogger(__name__)


def _actually_load_module(extension_path: str, fullname: str):
    import importlib.util

    spec = importlib.util.spec_from_file_location(fullname, extension_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def load_module(extension_path: str, fullname: str):
    with dlopen_flags():
        return _actually_load_module(extension_path, fullname)


@contextmanager
def dlopen_flags():
    # See `rustimport.settings.rtld_flags` for an explanation

    if hasattr(sys, "getdlopenflags"):
        old_flags = sys.getdlopenflags()
        new_flags = old_flags | settings.rtld_flags

        try:
            sys.setdlopenflags(new_flags)
            yield
        finally:
            sys.setdlopenflags(old_flags)
    else:
        yield
