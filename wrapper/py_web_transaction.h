#ifndef PY_WRAPPER_WEB_TRANSACTION_H
#define PY_WRAPPER_WEB_TRANSACTION_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include <Python.h>

#include "application_data.h"
#include "web_transaction_data.h"

/* ------------------------------------------------------------------------- */

typedef struct {
    PyObject_HEAD
    nr_application *application;
    nr_web_transaction *web_transaction;
} NRWebTransactionObject;

extern PyTypeObject NRWebTransaction_Type;

/* ------------------------------------------------------------------------- */

extern NRWebTransactionObject *NRWebTransaction_New(
        nr_application *application, PyObject *environ);

/* ------------------------------------------------------------------------- */

#endif
