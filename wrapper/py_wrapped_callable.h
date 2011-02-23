#ifndef PY_WRAPPER_WRAPPED_CALLABLE_H
#define PY_WRAPPER_WRAPPED_CALLABLE_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include <Python.h>

/* ------------------------------------------------------------------------- */

#define NR_FUNCTION_TYPE_PRE_FUNCTION 0
#define NR_FUNCTION_TYPE_POST_FUNCTION 1
#define NR_FUNCTION_TYPE_PASS_FUNCTION 2

typedef struct {
    PyObject_HEAD
    PyObject *wrapped_object;
    int function_type;
    PyObject *function_object;
    int run_once;
} NRWrappedCallableObject;

extern PyTypeObject NRWrappedCallable_Type;

/* ------------------------------------------------------------------------- */

extern PyObject *NRWrappedCallable_WrapPreFunction(const char *module_name,
                                                   const char *class_name,
                                                   const char *name,
                                                   PyObject *function,
                                                   int run_once);

/* ------------------------------------------------------------------------- */

#endif

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
