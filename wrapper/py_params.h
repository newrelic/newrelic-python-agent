#ifndef PY_WRAPPER_PARAMS_H
#define PY_WRAPPER_PARAMS_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "params_funcs.h"

#include <Python.h>

/* ------------------------------------------------------------------------- */

extern void nrpy__merge_dict_into_params_at(nr_param_array* array,
                                            const char *name, PyObject *dict);

/* ------------------------------------------------------------------------- */

#endif
