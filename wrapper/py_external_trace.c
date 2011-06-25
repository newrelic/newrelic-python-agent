/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_external_trace.h"

#include "py_utilities.h"

#include "globals.h"

#include "web_transaction.h"

#include "structmember.h"

/* ------------------------------------------------------------------------- */

static PyObject *NRExternalTrace_new(PyTypeObject *type, PyObject *args,
                                     PyObject *kwds)
{
    NRExternalTraceObject *self;

    /*
     * Allocate the transaction object and initialise it as per
     * normal.
     */

    self = (NRExternalTraceObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->parent_transaction = NULL;
    self->transaction_trace = NULL;
    self->saved_trace_node = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRExternalTrace_init(NRExternalTraceObject *self, PyObject *args,
                                PyObject *kwds)
{
    NRTransactionObject *transaction = NULL;

    PyObject *library = NULL;
    PyObject *url = NULL;

    static char *kwlist[] = { "transaction", "library", "url", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O!OO:ExternalTrace",
                                     kwlist, &NRTransaction_Type,
                                     &transaction, &library, &url)) {
        return -1;
    }

    if (!PyString_Check(library) && !PyUnicode_Check(library)) {
        PyErr_Format(PyExc_TypeError, "expected string or Unicode for "
                     "library, found type '%s'", library->ob_type->tp_name);
        return -1;
    }

    if (!PyString_Check(url) && !PyUnicode_Check(url)) {
        PyErr_Format(PyExc_TypeError, "expected string or Unicode for "
                     "url, found type '%s'", url->ob_type->tp_name);
        return -1;
    }

    /*
     * Validate that this method hasn't been called previously.
     */

    if (self->parent_transaction) {
        PyErr_SetString(PyExc_TypeError, "trace already initialized");
        return -1;
    }

    /*
     * Validate that the parent transaction has been started.
     */

    if (transaction->transaction_state != NR_TRANSACTION_STATE_RUNNING) {
        PyErr_SetString(PyExc_RuntimeError, "transaction not active");
        return -1;
    }

    /*
     * Keep reference to parent transaction to ensure that it
     * is not destroyed before any trace created against it.
     */

    Py_INCREF(transaction);
    self->parent_transaction = transaction;

    /*
     * Don't need to create the inner agent transaction trace
     * node when executing against a dummy transaction.
     */

    if (transaction->transaction) {
        PyObject *module = NULL;

        PyObject *library_as_bytes = NULL;
        PyObject *url_as_bytes = NULL;

        PyObject *host_as_bytes = NULL;
        PyObject *path_as_bytes = NULL;

        const char *host_as_char = NULL;
        const char *library_as_char = NULL;
        const char *path_as_char = NULL;

        int fragment_len = 0;
        char *fragment = NULL;

        if (PyUnicode_Check(library)) {
            library_as_bytes = PyUnicode_AsUTF8String(library);
            library_as_char = PyString_AsString(library_as_bytes);
        }
        else
            library_as_char = PyString_AsString(library);

        if (PyUnicode_Check(url)) {
            url_as_bytes = PyUnicode_AsUTF8String(url);
        }
        else {
            Py_INCREF(url);
            url_as_bytes = url;
        }

        /*
	 * We need to extract from the URL the host and the
	 * path. For host we need to drop any username and
	 * password but preserve the port. If there is a port we
	 * use it, else we add back in port based on the scheme.
	 * We also drop any query string arguments.
         *
         * XXX Use urlparse module to do this work for now.
         * Later on we could implement as C code but lets make
         * sure we get it correct first.
         */

        module = PyImport_ImportModule("urlparse");

        if (module) {
            PyObject *func = NULL;

            func = PyObject_GetAttrString(module, "urlparse");

            if (func) {
                PyObject *result = NULL;

                result = PyObject_CallFunctionObjArgs(func, url_as_bytes,
                                                       NULL);

                if (result) {
                    const char *at = NULL;

                    host_as_bytes = PyTuple_GetItem(result, 1);
                    Py_INCREF(host_as_bytes);

                    host_as_char = PyString_AsString(host_as_bytes);

                    at = strchr(host_as_char, '@');
                    if (at)
                        host_as_char = at + 1;

                    path_as_bytes = PyTuple_GetItem(result, 2);
                    Py_INCREF(path_as_bytes);

                    path_as_char = PyString_AsString(path_as_bytes);
                }
                else {
                    host_as_char = "unknown";
                    path_as_char = PyString_AsString(url_as_bytes);
                }

                Py_XDECREF(result);
            }
            else {
                host_as_char = "unknown";
                path_as_char = PyString_AsString(url_as_bytes);
            }

            Py_XDECREF(func);
        }
        else {
            host_as_char = "unknown";
            path_as_char = PyString_AsString(url_as_bytes);
        }

        PyErr_Clear();

        /*
         * Make sure we drop leading slashes from the path as
         * we use that as the separater below.
         */

        while (*path_as_char == '/')
            path_as_char++;

        /*
         * Now we join the parts back together in the form
         * library/host/path.
         */

        fragment_len += strlen(host_as_char);
        fragment_len += strlen(library_as_char);
        fragment_len += strlen(path_as_char);
        fragment_len += 3;

        fragment = alloca(fragment_len);

        sprintf(fragment, "%s/%s/%s", host_as_char, library_as_char,
                path_as_char);

        self->transaction_trace =
                nr_web_transaction__allocate_external_node(
                transaction->transaction, fragment);

        Py_XDECREF(library_as_bytes);
        Py_XDECREF(url_as_bytes);

        Py_XDECREF(host_as_bytes);
        Py_XDECREF(path_as_bytes);
    }

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRExternalTrace_dealloc(NRExternalTraceObject *self)
{
    Py_XDECREF(self->parent_transaction);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRExternalTrace_enter(NRExternalTraceObject *self,
                                        PyObject *args)
{
    if (!self->transaction_trace) {
        Py_INCREF(self);
        return (PyObject *)self;
    }

    nr_node_header__record_starttime_and_push_current(
            (nr_node_header *)self->transaction_trace,
            &self->saved_trace_node);

    Py_INCREF(self);
    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRExternalTrace_exit(NRExternalTraceObject *self,
                                       PyObject *args)
{
    nr_web_transaction *transaction;
    nr_transaction_node *transaction_trace;

    transaction_trace = self->transaction_trace;

    if (!transaction_trace) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    nr_node_header__record_stoptime_and_pop_current(
            (nr_node_header *)transaction_trace, &self->saved_trace_node);

    transaction = self->parent_transaction->transaction;

    nr__generate_external_metrics_for_node_1(transaction_trace, transaction);

    if (!nr_node_header__delete_if_not_slow_enough(
            (nr_node_header *)transaction_trace, 1, transaction)) {
        nr_web_transaction__convert_from_stack_based(transaction_trace,
                transaction);
    }

    self->saved_trace_node = NULL;

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyMethodDef NRExternalTrace_methods[] = {
    { "__enter__",  (PyCFunction)NRExternalTrace_enter,  METH_NOARGS, 0 },
    { "__exit__",   (PyCFunction)NRExternalTrace_exit,   METH_VARARGS, 0 },
    { NULL, NULL }
};

static PyGetSetDef NRExternalTrace_getset[] = {
    { NULL },
};

PyTypeObject NRExternalTrace_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.ExternalTrace", /*tp_name*/
    sizeof(NRExternalTraceObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRExternalTrace_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    0,                      /*tp_call*/
    0,                      /*tp_str*/
    0,                      /*tp_getattro*/
    0,                      /*tp_setattro*/
    0,                      /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT,     /*tp_flags*/
    0,                      /*tp_doc*/
    0,                      /*tp_traverse*/
    0,                      /*tp_clear*/
    0,                      /*tp_richcompare*/
    0,                      /*tp_weaklistoffset*/
    0,                      /*tp_iter*/
    0,                      /*tp_iternext*/
    NRExternalTrace_methods, /*tp_methods*/
    0,                      /*tp_members*/
    NRExternalTrace_getset, /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)NRExternalTrace_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRExternalTrace_new,    /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRExternalTraceWrapper_new(PyTypeObject *type, PyObject *args,
                                           PyObject *kwds)
{
    NRExternalTraceWrapperObject *self;

    self = (NRExternalTraceWrapperObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->dict = NULL;
    self->next_object = NULL;
    self->last_object = NULL;
    self->library = NULL;
    self->url = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRExternalTraceWrapper_init(NRExternalTraceWrapperObject *self,
                                       PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;
    PyObject *library = NULL;
    PyObject *url = NULL;

    PyObject *object = NULL;

    static char *kwlist[] = { "wrapped", "library", "url", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OOO:ExternalTraceWrapper",
                                     kwlist, &wrapped_object, &library,
                                     &url)) {
        return -1;
    }

    Py_INCREF(wrapped_object);

    Py_XDECREF(self->dict);
    Py_XDECREF(self->next_object);
    Py_XDECREF(self->last_object);

    self->next_object = wrapped_object;
    self->last_object = NULL;
    self->dict = NULL;

    object = PyObject_GetAttrString(wrapped_object, "__newrelic__");

    if (object) {
        Py_DECREF(object);

        object = PyObject_GetAttrString(wrapped_object, "__last_object__");

        if (object)
            self->last_object = object;
        else
            PyErr_Clear();
    }
    else
        PyErr_Clear();

    if (!self->last_object) {
        Py_INCREF(wrapped_object);
        self->last_object = wrapped_object;
    }

    object = PyObject_GetAttrString(self->last_object, "__dict__");

    if (object)
        self->dict = object;
    else
        PyErr_Clear();

    Py_INCREF(library);
    Py_XDECREF(self->library);
    self->library = library;

    Py_INCREF(url);
    Py_XDECREF(self->url);
    self->url = url;

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRExternalTraceWrapper_dealloc(NRExternalTraceWrapperObject *self)
{
    Py_XDECREF(self->dict);

    Py_XDECREF(self->next_object);
    Py_XDECREF(self->last_object);

    Py_XDECREF(self->library);
    Py_XDECREF(self->url);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRExternalTraceWrapper_call(
        NRExternalTraceWrapperObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_result = NULL;

    PyObject *current_transaction = NULL;
    PyObject *external_trace = NULL;

    PyObject *instance_method = NULL;
    PyObject *method_args = NULL;
    PyObject *method_result = NULL;

    PyObject *url = NULL;

    /*
     * If there is no current transaction then we can call
     * the wrapped function and return immediately.
     */

    current_transaction = NRTransaction_CurrentTransaction();

    if (!current_transaction)
        return PyObject_Call(self->next_object, args, kwds);

    /* Create external trace context manager. */

    if (PyString_Check(self->url) || PyUnicode_Check(self->url)) {
        url = self->url;
        Py_INCREF(url);
    }
    else {
        /*
         * Name if actually a callable function to provide the
         * name based on arguments supplied to wrapped function.
         */

        url = PyObject_Call(self->url, args, kwds);

        if (!url)
            return NULL;
    }

    external_trace = PyObject_CallFunctionObjArgs((PyObject *)
            &NRExternalTrace_Type, current_transaction, self->library,
            url, NULL);

    Py_DECREF(url);

    if (!external_trace)
        return NULL;

    /* Now call __enter__() on the context manager. */

    instance_method = PyObject_GetAttrString(external_trace, "__enter__");

    method_args = PyTuple_Pack(0);
    method_result = PyObject_Call(instance_method, method_args, NULL);

    if (!method_result)
        PyErr_WriteUnraisable(instance_method);
    else
        Py_DECREF(method_result);

    Py_DECREF(method_args);
    Py_DECREF(instance_method);

    /*
     * Now call the actual wrapped function with the original
     * position and keyword arguments.
     */

    wrapped_result = PyObject_Call(self->next_object, args, kwds);

    /*
     * Now call __exit__() on the context manager. If the call
     * of the wrapped function is successful then pass all None
     * objects, else pass exception details.
     */

    instance_method = PyObject_GetAttrString(external_trace, "__exit__");

    if (wrapped_result) {
        method_args = PyTuple_Pack(3, Py_None, Py_None, Py_None);
        method_result = PyObject_Call(instance_method, method_args, NULL);

        if (!method_result)
            PyErr_WriteUnraisable(instance_method);
        else
            Py_DECREF(method_result);

        Py_DECREF(method_args);
        Py_DECREF(instance_method);
    }
    else {
        PyObject *type = NULL;
        PyObject *value = NULL;
        PyObject *traceback = NULL;

        PyErr_Fetch(&type, &value, &traceback);

        if (!value) {
            value = Py_None;
            Py_INCREF(value);
        }

        if (!traceback) {
            traceback = Py_None;
            Py_INCREF(traceback);
        }

        PyErr_NormalizeException(&type, &value, &traceback);

        method_args = PyTuple_Pack(3, type, value, traceback);
        method_result = PyObject_Call(instance_method, method_args, NULL);

        if (!method_result)
            PyErr_WriteUnraisable(instance_method);
        else
            Py_DECREF(method_result);

        Py_DECREF(method_args);
        Py_DECREF(instance_method);

        PyErr_Restore(type, value, traceback);
    }

    Py_DECREF(external_trace);

    return wrapped_result;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRExternalTraceWrapper_get_next(
        NRExternalTraceWrapperObject *self, void *closure)
{
    if (!self->next_object) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    Py_INCREF(self->next_object);
    return self->next_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRExternalTraceWrapper_get_last(
        NRExternalTraceWrapperObject *self, void *closure)
{
    if (!self->last_object) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    Py_INCREF(self->last_object);
    return self->last_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRExternalTraceWrapper_get_marker(
        NRExternalTraceWrapperObject *self, void *closure)
{
    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRExternalTraceWrapper_get_module(
        NRExternalTraceWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    return PyObject_GetAttrString(self->last_object, "__module__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRExternalTraceWrapper_get_name(
        NRExternalTraceWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    return PyObject_GetAttrString(self->last_object, "__name__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRExternalTraceWrapper_get_doc(
        NRExternalTraceWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    return PyObject_GetAttrString(self->last_object, "__doc__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRExternalTraceWrapper_get_dict(
        NRExternalTraceWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    if (self->dict) {
        Py_INCREF(self->dict);
        return self->dict;
    }

    return PyObject_GetAttrString(self->last_object, "__dict__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRExternalTraceWrapper_getattro(
        NRExternalTraceWrapperObject *self, PyObject *name)
{
    PyObject *object = NULL;

    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    object = PyObject_GenericGetAttr((PyObject *)self, name);

    if (object)
        return object;

    PyErr_Clear();

    return PyObject_GetAttr(self->last_object, name);
}

/* ------------------------------------------------------------------------- */

static int NRExternalTraceWrapper_setattro(
        NRExternalTraceWrapperObject *self, PyObject *name, PyObject *value)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return -1;
    }

    return PyObject_SetAttr(self->last_object, name, value);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRExternalTraceWrapper_descr_get(PyObject *function,
                                                PyObject *object,
                                                PyObject *type)
{
    if (object == Py_None)
        object = NULL;

    return PyMethod_New(function, object, type);
}

/* ------------------------------------------------------------------------- */

static PyGetSetDef NRExternalTraceWrapper_getset[] = {
    { "__next_object__",    (getter)NRExternalTraceWrapper_get_next,
                            NULL, 0 },
    { "__last_object__",    (getter)NRExternalTraceWrapper_get_last,
                            NULL, 0 },
    { "__newrelic__",       (getter)NRExternalTraceWrapper_get_marker,
                            NULL, 0 },
    { "__module__",         (getter)NRExternalTraceWrapper_get_module,
                            NULL, 0 },
    { "__name__",           (getter)NRExternalTraceWrapper_get_name,
                            NULL, 0 },
    { "__doc__",            (getter)NRExternalTraceWrapper_get_doc,
                            NULL, 0 },
    { "__dict__",           (getter)NRExternalTraceWrapper_get_dict,
                            NULL, 0 },
    { NULL },
};

PyTypeObject NRExternalTraceWrapper_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.ExternalTraceWrapper", /*tp_name*/
    sizeof(NRExternalTraceWrapperObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRExternalTraceWrapper_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRExternalTraceWrapper_call, /*tp_call*/
    0,                      /*tp_str*/
    (getattrofunc)NRExternalTraceWrapper_getattro, /*tp_getattro*/
    (setattrofunc)NRExternalTraceWrapper_setattro, /*tp_setattro*/
    0,                      /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT,     /*tp_flags*/
    0,                      /*tp_doc*/
    0,                      /*tp_traverse*/
    0,                      /*tp_clear*/
    0,                      /*tp_richcompare*/
    0,                      /*tp_weaklistoffset*/
    0,                      /*tp_iter*/
    0,                      /*tp_iternext*/
    0,                      /*tp_methods*/
    0,                      /*tp_members*/
    NRExternalTraceWrapper_getset, /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    NRExternalTraceWrapper_descr_get, /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    offsetof(NRExternalTraceWrapperObject, dict), /*tp_dictoffset*/
    (initproc)NRExternalTraceWrapper_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRExternalTraceWrapper_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRExternalTraceDecorator_new(PyTypeObject *type,
                                              PyObject *args, PyObject *kwds)
{
    NRExternalTraceDecoratorObject *self;

    self = (NRExternalTraceDecoratorObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->library = NULL;
    self->url = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRExternalTraceDecorator_init(NRExternalTraceDecoratorObject *self,
                                         PyObject *args, PyObject *kwds)
{
    PyObject *library = NULL;
    PyObject *url = NULL;

    static char *kwlist[] = { "library", "url", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OO:ExternalTraceDecorator",
                                     kwlist, &library, &url)) {
        return -1;
    }

    Py_INCREF(library);
    Py_XDECREF(self->library);
    self->library = library;

    Py_INCREF(url);
    Py_XDECREF(self->url);
    self->url = url;

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRExternalTraceDecorator_dealloc(
        NRExternalTraceDecoratorObject *self)
{
    Py_DECREF(self->library);
    Py_DECREF(self->url);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRExternalTraceDecorator_call(
        NRExternalTraceDecoratorObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;

    static char *kwlist[] = { "wrapped", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:ExternalTraceDecorator",
                                     kwlist, &wrapped_object)) {
        return NULL;
    }

    return PyObject_CallFunctionObjArgs(
            (PyObject *)&NRExternalTraceWrapper_Type,
            wrapped_object, self->library, self->url, NULL);
}

/* ------------------------------------------------------------------------- */

PyTypeObject NRExternalTraceDecorator_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.ExternalTraceDecorator", /*tp_name*/
    sizeof(NRExternalTraceDecoratorObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRExternalTraceDecorator_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRExternalTraceDecorator_call, /*tp_call*/
    0,                      /*tp_str*/
    0,                      /*tp_getattro*/
    0,                      /*tp_setattro*/
    0,                      /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT,     /*tp_flags*/
    0,                      /*tp_doc*/
    0,                      /*tp_traverse*/
    0,                      /*tp_clear*/
    0,                      /*tp_richcompare*/
    0,                      /*tp_weaklistoffset*/
    0,                      /*tp_iter*/
    0,                      /*tp_iternext*/
    0,                      /*tp_methods*/
    0,                      /*tp_members*/
    0,                      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)NRExternalTraceDecorator_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRExternalTraceDecorator_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

/*
 * vim: set cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
