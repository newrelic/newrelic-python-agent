#ifndef PY_WRAPPER_PRE_FUNCTION_H
#define PY_WRAPPER_PRE_FUNCTION_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_python.h"

/* ------------------------------------------------------------------------- */

typedef struct {
    PyObject_HEAD
    PyObject *dict;
    PyObject *wrapped_object;
    PyObject *function_object;
    int run_once;
} NRPreFunctionWrapperObject;

extern PyTypeObject NRPreFunctionWrapper_Type;

typedef struct {
    PyObject_HEAD
    PyObject *function_object;
    int run_once;
} NRPreFunctionDecoratorObject;

extern PyTypeObject NRPreFunctionDecorator_Type;

/* ------------------------------------------------------------------------- */

#endif

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
