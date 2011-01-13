#ifndef PY_WRAPPER_DATABASE_TRACE_H
#define PY_WRAPPER_DATABASE_TRACE_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include <Python.h>

#include "web_transaction_data.h"

/* ------------------------------------------------------------------------- */

typedef struct {
    PyObject_HEAD
    nr_transaction_node *transaction_trace;
    nr_node_header* outer_transaction;
} NRDatabaseTraceObject;

extern PyTypeObject NRDatabaseTrace_Type;

/* ------------------------------------------------------------------------- */

extern NRDatabaseTraceObject *NRDatabaseTrace_New(
        nr_web_transaction *transaction, const char *url);

/* ------------------------------------------------------------------------- */

#endif
