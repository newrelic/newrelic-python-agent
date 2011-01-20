#ifndef PY_WRAPPER_TRACEBACK_H
#define PY_WRAPPER_TRACEBACK_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include <Python.h>

/* ------------------------------------------------------------------------- */

extern PyObject *nrpy__format_exception(PyObject *type, PyObject *value,
                                        PyObject *traceback);

/* ------------------------------------------------------------------------- */

#endif
