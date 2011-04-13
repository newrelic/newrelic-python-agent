#ifndef PY_WRAPPER_TRANSACTION_H
#define PY_WRAPPER_TRANSACTION_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_application.h"

/* ------------------------------------------------------------------------- */

#define NR_TRANSACTION_STATE_PENDING 0
#define NR_TRANSACTION_STATE_RUNNING 1
#define NR_TRANSACTION_STATE_STOPPED 2

typedef struct {
    PyObject_HEAD
    NRApplicationObject *application;
    nr_web_transaction *transaction;
    nr_node_header** most_expensive_nodes;
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

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
