#ifndef PY_WRAPPER_PARAMS_H
#define PY_WRAPPER_PARAMS_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "globals.h"
#include "nrtypes.h"

#include <Python.h>

/* ------------------------------------------------------------------------- */

extern void nrpy__merge_dict_into_params_at(nrobj_t array,
                                            const char *name, PyObject *dict);

/* ------------------------------------------------------------------------- */

#endif
