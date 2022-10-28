__version_info__ = ("1", "14", "1")
__version__ = ".".join(__version_info__)

from inspect import getcallargs

from .arguments import formatargspec
from .decorators import AdapterFactory, adapter_factory, decorator, synchronized
from .importer import (
    discover_post_import_hooks,
    notify_module_loaded,
    register_post_import_hook,
    when_imported,
)
from .wrappers import (
    BoundFunctionWrapper,
    CallableObjectProxy,
    FunctionWrapper,
    ObjectProxy,
    PartialCallableObjectProxy,
    WeakFunctionProxy,
    apply_patch,
    function_wrapper,
    patch_function_wrapper,
    resolve_path,
    transient_function_wrapper,
    wrap_function_wrapper,
    wrap_object,
    wrap_object_attribute,
)

# Import of inspect.getcallargs() included for backward compatibility. An
# implementation of this was previously bundled and made available here for
# Python <2.7. Avoid using this in future.


# Variant of inspect.formatargspec() included here for forward compatibility.
# This is being done because Python 3.11 dropped inspect.formatargspec() but
# code for handling signature changing decorators relied on it. Exposing the
# bundled implementation here in case any user of wrapt was also needing it.
