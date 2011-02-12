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

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
