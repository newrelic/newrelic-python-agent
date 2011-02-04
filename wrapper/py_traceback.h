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

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
