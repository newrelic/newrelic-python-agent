This directory includes wrappers for both code files and header files in
the PHP agent code directory that we require for the Python agent. This
includes dummy PHP include files and special fixup file that allows
dependencies on PHP code in generic parts of PHP code to be nullified,
allowing it to be compiled unmodified into Python agent.

Yes this is all a big hack, but until the existing PHP agent code is
refactored so that generic parts are separated into a distinct library with
no PHP dependencies, then this is the easiest thing to do, allow the PHP
agent trunk to be used without needing to modify it.
