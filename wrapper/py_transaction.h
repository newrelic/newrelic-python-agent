#ifndef PY_WRAPPER_TRANSACTION_H
#define PY_WRAPPER_TRANSACTION_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include <Python.h>

#include "py_application.h"

#include "application_data.h"
#include "web_transaction_data.h"

/* ------------------------------------------------------------------------- */

typedef struct {
    PyObject_HEAD
    int initialised;
    NRApplicationObject *application;
    nr_web_transaction *transaction;
    nr_transaction_error* transaction_errors;
    PyObject *request_parameters;
    PyObject *custom_parameters;
    int transaction_enabled;
    int transaction_active;
} NRTransactionObject;

extern PyTypeObject NRTransaction_Type;

/* ------------------------------------------------------------------------- */

extern NRTransactionObject *NRTransaction_CurrentTransaction(void);

/* ------------------------------------------------------------------------- */

#endif
