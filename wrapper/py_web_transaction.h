#ifndef PY_WRAPPER_WEB_TRANSACTION_H
#define PY_WRAPPER_WEB_TRANSACTION_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_transaction.h"

/* ------------------------------------------------------------------------- */

extern PyTypeObject NRWebTransaction_Type;

typedef struct {
    PyObject_HEAD
    PyObject *application;
    PyObject *wrapped_object;
    PyObject *environ;
    PyObject *start_response;
    PyObject *transaction;
    PyObject *result;
    PyObject *iterable;
} NRWebTransactionIterableObject;

extern PyTypeObject NRWebTransactionIterable_Type;

typedef struct {
    PyObject_HEAD
    PyObject *application;
    PyObject *wrapped_object;
} NRWebTransactionWrapperObject;

extern PyTypeObject NRWebTransactionWrapper_Type;

typedef struct {
    PyObject_HEAD
    PyObject *application;
} NRWebTransactionDecoratorObject;

extern PyTypeObject NRWebTransactionDecorator_Type;

/* ------------------------------------------------------------------------- */

#endif

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
