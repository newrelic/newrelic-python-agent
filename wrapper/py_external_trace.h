#ifndef PY_WRAPPER_EXTERNAL_TRACE_H
#define PY_WRAPPER_EXTERNAL_TRACE_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include <Python.h>

#include "web_transaction_data.h"

/* ------------------------------------------------------------------------- */

typedef struct {
    PyObject_HEAD
    nr_transaction_node *transaction_trace;
    nr_node_header* outer_transaction;
} NRExternalTraceObject;

extern PyTypeObject NRExternalTrace_Type;

/* ------------------------------------------------------------------------- */

extern NRExternalTraceObject *NRExternalTrace_New(
        nr_web_transaction *transaction, const char *url);

/* ------------------------------------------------------------------------- */

#endif
