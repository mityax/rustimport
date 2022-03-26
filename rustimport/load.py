import logging
import sys

from rustimport import settings

logger = logging.getLogger(__name__)


def _actually_load_module(extension_path: str, fullname: str):
    import importlib.util

    spec = importlib.util.spec_from_file_location(fullname, extension_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module

    #return importlib.import_module(fullname)


def load_module(extension_path: str, fullname: str):
    if hasattr(sys, "getdlopenflags"):
        # See `rustimport.settings.rtld_flags` for an explanation
        old_flags = sys.getdlopenflags()
        new_flags = old_flags | settings.rtld_flags
        sys.setdlopenflags(new_flags)
        module = _actually_load_module(extension_path, fullname)
        sys.setdlopenflags(old_flags)
        return module
    else:
        return _actually_load_module(extension_path, fullname)
