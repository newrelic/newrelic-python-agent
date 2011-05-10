#ifndef PY_WRAPPER_UTILITIES_H
#define PY_WRAPPER_UTILITIES_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "globals.h"
#include "nrtypes.h"

#include <Python.h>

/* ------------------------------------------------------------------------- */

extern PyObject *NRUtilities_FormatException(PyObject *type, PyObject *value,
                                             PyObject *traceback);

extern PyObject *NRUtilities_CallableName(PyObject *wrapped,
                                          PyObject *wrapper,
                                          PyObject *args);

extern PyObject *NRUtilities_ResolveObject(PyObject *module,
                                           PyObject *object_name,
                                           PyObject **parent_object,
                                           PyObject **attribute_name);

extern PyObject *NRUtilities_ObjectContext(PyObject *wrapped,
                                           PyObject *wrapper,
                                           PyObject *args);

extern PyObject *NRUtilities_ReplaceWithWrapper(PyObject *parent_object,
                                                PyObject *attribute_name,
                                                PyObject *wrapper_object);

extern void NRUtilities_MergeDictIntoParams(nrobj_t array,
                                            const char *name,
                                            PyObject *dict);

extern PyObject *NRUtilities_StackTrace(void);

extern PyObject *NRUtilities_ObfuscateTransactionName(const char *name,
                                                      const char *license_key);

/* ------------------------------------------------------------------------- */

#endif

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
