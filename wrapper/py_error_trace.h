#ifndef PY_WRAPPER_ERROR_TRACE_H
#define PY_WRAPPER_ERROR_TRACE_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_transaction.h"

/* ------------------------------------------------------------------------- */

typedef struct {
    PyObject_HEAD
    NRTransactionObject *parent_transaction;
} NRErrorTraceObject;

extern PyTypeObject NRErrorTrace_Type;

typedef struct {
    PyObject_HEAD
    PyObject *wrapped_object;
} NRErrorTraceWrapperObject;

extern PyTypeObject NRErrorTraceWrapper_Type;

typedef struct {
    PyObject_HEAD
} NRErrorTraceDecoratorObject;

extern PyTypeObject NRErrorTraceDecorator_Type;

/* ------------------------------------------------------------------------- */

#endif

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
