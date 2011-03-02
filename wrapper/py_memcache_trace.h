#ifndef PY_WRAPPER_MEMCACHE_TRACE_H
#define PY_WRAPPER_MEMCACHE_TRACE_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_transaction.h"

/* ------------------------------------------------------------------------- */

typedef struct {
    PyObject_HEAD
    NRTransactionObject *parent_transaction;
    nr_transaction_node *transaction_trace;
    nr_node_header* saved_trace_node;
} NRMemcacheTraceObject;

extern PyTypeObject NRMemcacheTrace_Type;

typedef struct {
    PyObject_HEAD
    PyObject *wrapped_object;
    PyObject *command;
} NRMemcacheTraceWrapperObject;

extern PyTypeObject NRMemcacheTraceWrapper_Type;

typedef struct {
    PyObject_HEAD
    PyObject *command;
} NRMemcacheTraceDecoratorObject;

extern PyTypeObject NRMemcacheTraceDecorator_Type;

/* ------------------------------------------------------------------------- */

#endif

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
