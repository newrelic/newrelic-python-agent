#ifndef PY_WRAPPER_TRANSACTION_H
#define PY_WRAPPER_TRANSACTION_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include <Python.h>

#include "py_application.h"

/* ------------------------------------------------------------------------- */

#define NR_TRANSACTION_STATE_PENDING 0
#define NR_TRANSACTION_STATE_RUNNING 1
#define NR_TRANSACTION_STATE_STOPPED 2

typedef struct {
    PyObject_HEAD
    NRApplicationObject *application;
    nr_web_transaction *transaction;
    nr_transaction_error* transaction_errors;
    PyObject *request_parameters;
    PyObject *custom_parameters;
    int transaction_state;
} NRTransactionObject;

extern PyTypeObject NRTransaction_Type;

/* ------------------------------------------------------------------------- */

extern PyObject *NRTransaction_CurrentTransaction(void);

/* ------------------------------------------------------------------------- */

#endif
