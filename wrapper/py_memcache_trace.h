#ifndef PY_WRAPPER_MEMCACHE_TRACE_H
#define PY_WRAPPER_MEMCACHE_TRACE_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include <Python.h>

#include "web_transaction_data.h"

/* ------------------------------------------------------------------------- */

typedef struct {
    PyObject_HEAD
    nr_transaction_node *transaction_trace;
} NRMemcacheTraceObject;

extern PyTypeObject NRMemcacheTrace_Type;

/* ------------------------------------------------------------------------- */

extern NRMemcacheTraceObject *NRMemcacheTrace_New(
        nr_web_transaction *transaction, const char *metric_fragment);

/* ------------------------------------------------------------------------- */

#endif
