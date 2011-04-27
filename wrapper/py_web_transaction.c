/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_web_transaction.h"

#include "globals.h"

#include "py_utilities.h"

/* ------------------------------------------------------------------------- */

static int NRWebTransaction_init(NRTransactionObject *self, PyObject *args,
                                 PyObject *kwds)
{
    NRApplicationObject *application = NULL;
    PyObject *environ = NULL;

    PyObject *enabled = NULL;
    PyObject *newargs = NULL;
    PyObject *object = NULL;

    static char *kwlist[] = { "application", "environ", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O!O!:WebTransaction",
                                     kwlist, &NRApplication_Type,
                                     &application, &PyDict_Type, &environ)) {
        return -1;
    }

    /*
     * Validate that this method hasn't been called previously.
     */

    if (self->application) {
        PyErr_SetString(PyExc_TypeError, "transaction already initialized");
        return -1;
    }

    /*
     * Transaction can be enabled/disabled by the value of the
     * variable "newrelic.enabled" in the WSGI environ
     * dictionary. Allow either boolean or string. In the case
     * of string a value of 'Off' (case insensitive) will
     * disable the transaction. We have to allow string as
     * SetEnv under Apache when passed through to WSGI environ
     * dictionary only allows for strings.
     */

    object = PyDict_GetItemString(environ, "newrelic.enabled");

    if (object) {
        if (PyBool_Check(object)) {
            enabled = object;
        }
        else if (PyString_Check(object)) {
            const char *value;

            value = PyString_AsString(object);

            if (!strcasecmp(value, "off"))
                enabled = Py_False;
            else
                enabled = Py_True;
        }
    }

    /*
     * Pass application object and optionally the enabled flag
     * to the base class constructor. Where enabled flag is
     * passed in, that takes precedence over what may be set in
     * the application object itself.
     */

    if (enabled)
        newargs = PyTuple_Pack(2, PyTuple_GetItem(args, 0), enabled);
    else
        newargs = PyTuple_Pack(1, PyTuple_GetItem(args, 0));

    if (NRTransaction_Type.tp_init((PyObject *)self, newargs, kwds) < 0) {
        Py_DECREF(newargs);
        return -1;
    }

    Py_DECREF(newargs);

    /*
     * Setup the web transaction specific attributes of the
     * transaction.
     */

    if (self->transaction) {
        /*
         * Extract from the WSGI environ dictionary details of
         * the URL path. This will be set as default path for
         * the web transaction. This can be overridden by
         * framework to be more specific to avoid metrics
         * explosion problem resulting from too many distinct
         * URLs for same resource due to use of REST style URL
         * concepts or otherwise.
         */

        self->transaction->path = 0;

        object = PyDict_GetItemString(environ, "REQUEST_URI");

        if (object && PyString_Check(object)) {
            self->transaction->path_type = NR_PATH_TYPE_URI;
            self->transaction->path = nrstrdup(PyString_AsString(object));
            self->transaction->realpath = nrstrdup(self->transaction->path);
        }
        else {
            const char *script_name = NULL;
            const char *path_info = NULL;

            object = PyDict_GetItemString(environ, "SCRIPT_NAME");

            if (object && PyString_Check(object))
                script_name = PyString_AsString(object);

            object = PyDict_GetItemString(environ, "PATH_INFO");

            if (object && PyString_Check(object))
                path_info = PyString_AsString(object);

            if (script_name || path_info) {
                char *path = NULL;

                self->transaction->path_type = NR_PATH_TYPE_URI;

                if (!script_name)
                    script_name = "";

                if (!path_info)
                    path_info = "";

                path = nrmalloc(strlen(script_name)+strlen(path_info)+1);

                strcpy(path, script_name);
                strcat(path, path_info);

                self->transaction->path = path;
                self->transaction->realpath = nrstrdup(path);
            }
        }

        if (self->transaction->path == 0) {
            self->transaction->path_type = NR_PATH_TYPE_UNKNOWN;
            self->transaction->path = nrstrdup("<unknown>");
            self->transaction->realpath = nrstrdup(self->transaction->path);
        }

        /*
         * See if the WSGI environ dictionary includes the
         * special 'X-NewRelic-Queue-Start' HTTP header. This
         * header is an optional header that can be set within
         * the underlying web server or WSGI server to indicate
         * when the current request was first received and ready
         * to be processed. The difference between this time and
         * when application starts processing the request is the
         * queue time and represents how long spent in any
         * explicit request queuing system, or how long waiting
         * in connecting state against listener sockets where
         * request needs to be proxied between any processes
         * within the application server.
         */

        self->transaction->http_x_request_start = 0;

        object = PyDict_GetItemString(environ, "HTTP_X_NEWRELIC_QUEUE_START");

        if (object && PyString_Check(object)) {
            const char *s = PyString_AsString(object);
            if (s[0] == 't' && s[1] == '=' ) {
                self->transaction->http_x_request_start = (int64_t)strtoll(
                        s+2, 0, 0);
            }
        }

        /*
         * Check whether web transaction being flagged as a
         * background task via variable in the WSGI environ
         * dictionary.
         */

        self->transaction->backgroundjob = 0;

        object = PyDict_GetItemString(environ, "newrelic.background_task");

        if (object) {
            if (PyBool_Check(object)) {
                if (object == Py_True)
                    self->transaction->backgroundjob = 1;
            }
            else if (PyString_Check(object)) {
                const char *value;

                value = PyString_AsString(object);

                if (!strcasecmp(value, "on"))
                    self->transaction->backgroundjob = 1;
            }
        }

        /*
         * Check whether web transaction being flagged as to be
         * ignored. This is different to being disabled
         * completely via the enabled flag as ignored state
         * could be undone where as for disabled case tracking
         * of transaction does not even occur.
         */

        self->transaction->ignore = 0;

        object = PyDict_GetItemString(environ, "newrelic.ignore_transaction");

        if (object) {
            if (PyBool_Check(object)) {
                if (object == Py_True)
                    self->transaction->ignore = 1;
            }
            else if (PyString_Check(object)) {
                const char *value;

                value = PyString_AsString(object);

                if (!strcasecmp(value, "on"))
                    self->transaction->ignore = 1;
            }
        }

        /*
         * Create a copy of the WSGI environ for the request
         * parameters. We don't just reference the original
         * environ dictionary as WSGI middleware may change the
         * content in place and so data could end up being
         * different to what it was at start of the request.
         */

        PyDict_Update(self->request_parameters, environ);
    }

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWebTransaction_header(NRTransactionObject *self,
                                         PyObject *args)
{
    const char *script_short_fragment = "<script>var NREUMQ=[];"
            "NREUMQ.push([\"mark\",\"firstbyte\",new Date().getTime()]);"
            "</script>";

    const char *script_long_fragment = "<script>var NREUMQ=[];"
            "NREUMQ.push([\"mark\",\"firstbyte\",new Date().getTime()]);"
            "(function(){var d=document;var e=d.createElement(\"script\");"
            "e.type=\"text/javascript\";e.async=true;e.src=\"%s\";"
            "var s=d.getElementsByTagName(\"script\")[0];"
            "s.parentNode.insertBefore(e,s);})();"
            "</script>";

    if (!self->transaction)
        return PyString_FromString("");

    if (self->transaction_state != NR_TRANSACTION_STATE_RUNNING)
        return PyString_FromString("");

    if (self->transaction->ignore)
        return PyString_FromString("");

    if (!self->application->application->episodes_url)
        return PyString_FromString("");

    self->transaction->has_returned_browser_timing_header = 1;

    if (!self->application->application->load_episodes_file)
        return PyString_FromString(script_short_fragment);

    return PyString_FromFormat(script_long_fragment,
            self->application->application->episodes_url);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWebTransaction_footer(NRTransactionObject *self,
                                         PyObject *args)
{
    const char *script_fragment = "<script type=\"text/javascript\" "
            "charset=\"utf-8\">NREUMQ.push([\"nrf2\",\"%s\",\"%s\",%d,"
            "\"%s\",%ld,%ld])</script>";

    struct timeval t;

    int64_t queue_time_usec = 0;
    int64_t start_time_usec = 0;
    int64_t stop_time_usec = 0;

    int64_t queue_duration_usec = 0;
    int64_t total_duration_usec = 0;

    PyObject *transaction_name = NULL;

    PyObject *result = NULL;

    if (!self->transaction)
        return PyString_FromString("");

    if (self->transaction_state != NR_TRANSACTION_STATE_RUNNING)
        return PyString_FromString("");

    if (self->transaction->ignore)
        return PyString_FromString("");

    if (!self->transaction->has_returned_browser_timing_header)
        return PyString_FromString("");

    if (!self->application->application->license_key ||
        strlen(self->application->application->license_key) < 13) {
        return PyString_FromString("");
    }

    transaction_name = NRUtilities_ObfuscateTransactionName(
            self->transaction->path,
            self->application->application->license_key);

    if (!transaction_name)
        return NULL;

    /*
     * The web transaction isn't over at this point so we need to
     * calculate time to now from start of the web transaction.
     */

    queue_time_usec = self->transaction->http_x_request_start;
    start_time_usec = self->transaction->header.times.starttime;

    gettimeofday(&t, NULL);
    stop_time_usec = ((int64_t)t.tv_sec) * 1000000 + ((int64_t)t.tv_usec);

    if (!queue_time_usec)
        queue_time_usec = start_time_usec;
        
    queue_duration_usec = start_time_usec - queue_time_usec;
    total_duration_usec = stop_time_usec - start_time_usec;

    result = PyString_FromFormat(script_fragment,
            self->application->application->beacon,
            self->application->application->browser_key,
            self->application->application->application_id,
            PyString_AsString(transaction_name),
            (long)(queue_duration_usec/1000),
            (long)(total_duration_usec/1000));

    Py_DECREF(transaction_name);

    return result;
}

/* ------------------------------------------------------------------------- */

static int NRWebTransaction_set_background_task(
        NRTransactionObject *self, PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "can't delete "
                        "background_task attribute");
        return -1;
    }

    if (!PyBool_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected bool for "
                        "background_task attribute");
        return -1;
    }

    /*
     * If the application was not enabled and so we are running
     * as a dummy transaction then return without actually doing
     * anything.
     */

    if (!self->transaction)
        return 0;

    if (value == Py_True)
        self->transaction->backgroundjob = 1;
    else
        self->transaction->backgroundjob = 0;

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWebTransaction_get_background_task(
        NRTransactionObject *self, void *closure)
{
    /*
     * If the application was not enabled and so we are running
     * as a dummy transaction then return that transaction is
     * being ignored.
     */

    if (!self->transaction) {
        Py_INCREF(Py_False);
        return Py_False;
    }

    return PyBool_FromLong(self->transaction->backgroundjob);
}

/* ------------------------------------------------------------------------- */

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

static PyMethodDef NRWebTransaction_methods[] = {
    { "browser_timing_header", (PyCFunction)NRWebTransaction_header,
                            METH_NOARGS, 0 },
    { "browser_timing_footer", (PyCFunction)NRWebTransaction_footer,
                            METH_NOARGS, 0 },
    { NULL, NULL }
};

static PyGetSetDef NRWebTransaction_getset[] = {
    { "background_task",    (getter)NRWebTransaction_get_background_task,
                            (setter)NRWebTransaction_set_background_task, 0 },
    { NULL },
};

PyTypeObject NRWebTransaction_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.WebTransaction", /*tp_name*/
    sizeof(NRTransactionObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    0,                      /*tp_dealloc*/
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
    NRWebTransaction_methods, /*tp_methods*/
    0,                      /*tp_members*/
    NRWebTransaction_getset, /*tp_getset*/
    &NRTransaction_Type,    /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)NRWebTransaction_init, /*tp_init*/
    0,                      /*tp_alloc*/
    0,                      /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRWebTransactionIterable_new(PyTypeObject *type,
                                              PyObject *args,
                                              PyObject *kwds)
{
    NRWebTransactionIterableObject *self;

    self = (NRWebTransactionIterableObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->application = NULL;
    self->wrapped_object = NULL;
    self->transaction = NULL;
    self->result = NULL;
    self->iterable = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRWebTransactionIterable_init(NRWebTransactionIterableObject *self,
                                         PyObject *args, PyObject *kwds)
{
    PyObject *application = NULL;
    PyObject *wrapped_object = NULL;
    PyObject *application_args = NULL;

    PyObject *environ = NULL;
    PyObject *start_response = NULL;

    PyObject *instance_method = NULL;
    PyObject *method_args = NULL;
    PyObject *method_result = NULL;

    int i = 0;

    static char *kwlist[] = { "application", "wrapped", "args", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds,
                                     "O!OO!:WebTransactionIterable",
                                     kwlist, &NRApplication_Type,
                                     &application, &wrapped_object,
                                     &PyTuple_Type, &application_args)) {
        return -1;
    }

    if (PyTuple_Size(application_args) < 2) {
        PyErr_SetString(PyExc_ValueError,
                        "insufficient application arguments");
        return -1;
    }

    Py_INCREF(application);
    Py_XDECREF(self->application);
    self->application = application;

    Py_INCREF(wrapped_object);
    Py_XDECREF(self->wrapped_object);
    self->wrapped_object = wrapped_object;

    start_response = PyTuple_GetItem(application_args,
                                     PyTuple_Size(application_args)-1);

    Py_INCREF(start_response);
    Py_XDECREF(self->start_response);
    self->start_response = start_response;

    environ = PyTuple_GetItem(application_args,
                              PyTuple_Size(application_args)-2);

    /* XXX So far assuming constructor not called twice. */

    self->transaction = PyObject_CallFunctionObjArgs((PyObject *)
            &NRWebTransaction_Type, self->application, environ, NULL);

    /* Now call __enter__() on the context manager. */

    instance_method = PyObject_GetAttrString(self->transaction, "__enter__");

    method_args = PyTuple_Pack(0);
    method_result = PyObject_Call(instance_method, method_args, NULL);

    if (!method_result)
        PyErr_WriteUnraisable(instance_method);
    else
        Py_DECREF(method_result);

    Py_DECREF(method_args);
    Py_DECREF(instance_method);

    /* Now call wrapper object to get the iterable it returns. */

    instance_method = PyObject_GetAttrString((PyObject *)self,
                                             "start_response");

    method_args = PyTuple_New(PyTuple_Size(application_args));

    for (i=0; i<PyTuple_Size(application_args)-1; i++) {
        PyObject *object = PyTuple_GetItem(application_args, i);
        Py_INCREF(object);
        PyTuple_SetItem(method_args, i, object);
    }

    PyTuple_SetItem(method_args, PyTuple_Size(application_args)-1,
                    instance_method);

    self->result = PyEval_CallObject(self->wrapped_object, method_args);

    Py_DECREF(method_args);

    /* It returned an error, call __exit__() on context manager. */

    if (!self->result) {
        PyObject *type = NULL;
        PyObject *value = NULL;
        PyObject *traceback = NULL;

        instance_method = PyObject_GetAttrString(self->transaction, "__exit__");

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

        return -1;
    }

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRWebTransactionIterable_dealloc(
        NRWebTransactionIterableObject *self)
{
    Py_XDECREF(self->application);
    Py_XDECREF(self->wrapped_object);
    Py_XDECREF(self->start_response);
    Py_XDECREF(self->transaction);
    Py_XDECREF(self->result);
    Py_XDECREF(self->iterable);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWebTransactionIterable_iter(
        NRWebTransactionIterableObject *self)
{
    self->iterable = PyObject_GetIter(self->result);

    Py_INCREF(self);
    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWebTransactionIterable_iternext(
        NRWebTransactionIterableObject *self)
{
    return PyIter_Next(self->iterable);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWebTransactionIterable_close(
        NRWebTransactionIterableObject *self, PyObject *args)
{
    PyObject *wrapped_method = NULL;
    PyObject *wrapped_result = NULL;

    PyObject *manager_method = NULL;

    PyObject *method_args = NULL;
    PyObject *method_result = NULL;

    if (self->iterable) {
        wrapped_method = PyObject_GetAttrString(self->iterable, "close");

        if (!wrapped_method) {
            PyErr_Clear();

            Py_INCREF(Py_None);
            wrapped_result = Py_None;
        }
        else
            wrapped_result = PyObject_CallFunctionObjArgs(wrapped_method, NULL);

        Py_XDECREF(wrapped_method);

    }
    else {
        Py_INCREF(Py_None);
        wrapped_result = Py_None;
    }

    /*
     * Now call __exit__() on the context manager. If the call
     * of the wrapped function is successful then pass all None
     * objects, else pass exception details.
     */

    manager_method = PyObject_GetAttrString(self->transaction, "__exit__");

    if (wrapped_result) {
        method_args = PyTuple_Pack(3, Py_None, Py_None, Py_None);
        method_result = PyObject_Call(manager_method, method_args, NULL);

        if (!method_result)
            PyErr_WriteUnraisable(manager_method);
        else
            Py_DECREF(method_result);

        Py_DECREF(method_args);
        Py_DECREF(manager_method);
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
        method_result = PyObject_Call(manager_method, method_args, NULL);

        if (!method_result)
            PyErr_WriteUnraisable(manager_method);
        else
            Py_DECREF(method_result);

        Py_DECREF(method_args);
        Py_DECREF(manager_method);

        PyErr_Restore(type, value, traceback);
    }

    return wrapped_result;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWebTransactionIterable_start(
        NRWebTransactionIterableObject *self, PyObject *args)
{
    PyObject *status_line = NULL;
    PyObject *headers = NULL;
    PyObject *exc_info = NULL;

    long status_as_int = 0;
    PyObject *status = NULL;

    if (!PyArg_ParseTuple(args, "O!O!|O!:start_response", &PyString_Type,
                          &status_line, &PyList_Type, &headers,
                          &PyTuple_Type, &exc_info)) {
        return NULL;
    }

    status_as_int = strtol(PyString_AsString(status_line), NULL, 10);
    status = PyInt_FromLong(status_as_int);

    if (PyObject_SetAttrString(self->transaction, "response_code",
                               status) == -1) {
        return NULL;
    }

    Py_DECREF(status);

    return PyEval_CallObject(self->start_response, args);
}

/* ------------------------------------------------------------------------- */

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

static PyMethodDef NRWebTransactionIterable_methods[] = {
    { "close",              (PyCFunction)NRWebTransactionIterable_close,
                            METH_NOARGS, 0 },
    { "start_response",     (PyCFunction)NRWebTransactionIterable_start,
                            METH_VARARGS, 0 },
    { NULL, NULL }
};

PyTypeObject NRWebTransactionIterable_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.WebTransactionIterable", /*tp_name*/
    sizeof(NRWebTransactionIterableObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRWebTransactionIterable_dealloc, /*tp_dealloc*/
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
    (getiterfunc)NRWebTransactionIterable_iter, /*tp_iter*/
    (iternextfunc)NRWebTransactionIterable_iternext, /*tp_iternext*/
    NRWebTransactionIterable_methods, /*tp_methods*/
    0,                      /*tp_members*/
    0,                      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)NRWebTransactionIterable_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRWebTransactionIterable_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRWebTransactionWrapper_new(PyTypeObject *type, PyObject *args,
                                           PyObject *kwds)
{
    NRWebTransactionWrapperObject *self;

    self = (NRWebTransactionWrapperObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->wrapped_object = NULL;
    self->application = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRWebTransactionWrapper_init(NRWebTransactionWrapperObject *self,
                                       PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;

    PyObject *application = Py_None;

    static char *kwlist[] = { "wrapped", "application", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OO:WebTransactionWrapper",
                                     kwlist, &wrapped_object, &application)) {
        return -1;
    }

    if (application != Py_None &&
        Py_TYPE(application) != &NRApplication_Type &&
        !PyString_Check(application) && !PyUnicode_Check(application)) {
        PyErr_Format(PyExc_TypeError, "application argument must be None, "
                     "str, unicode, or application object, found type '%s'",
                     application->ob_type->tp_name);
        return -1;
    }

    if (Py_TYPE(application) != &NRApplication_Type) {
        PyObject *func_args;

        if (application == Py_None) {
            application = PyString_FromString(nr_per_process_globals.appname);
            func_args = PyTuple_Pack(1, application);
            Py_DECREF(application);
            application = Py_None;
        }
        else
            func_args = PyTuple_Pack(1, application);

        application = NRApplication_Singleton(func_args, NULL);

        Py_DECREF(func_args);
    }
    else
        Py_INCREF(application);

    Py_INCREF(wrapped_object);
    Py_XDECREF(self->wrapped_object);
    self->wrapped_object = wrapped_object;

    Py_INCREF(application);
    Py_XDECREF(self->application);
    self->application = application;

    /*
     * TODO This should set __module__, __name__, __doc__ and
     * update __dict__ to preserve introspection capabilities.
     * See @wraps in functools of recent Python versions.
     */

    Py_DECREF(application);

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRWebTransactionWrapper_dealloc(NRWebTransactionWrapperObject *self)
{
    Py_XDECREF(self->wrapped_object);

    Py_XDECREF(self->application);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWebTransactionWrapper_call(
        NRWebTransactionWrapperObject *self, PyObject *args, PyObject *kwds)
{
    return PyObject_CallFunctionObjArgs((PyObject *)
            &NRWebTransactionIterable_Type, self->application,
            self->wrapped_object, args, NULL);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWebTransactionWrapper_get_name(
        NRWebTransactionWrapperObject *self, void *closure)
{
    return PyObject_GetAttrString(self->wrapped_object, "__name__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWebTransactionWrapper_get_module(
        NRWebTransactionWrapperObject *self, void *closure)
{
    return PyObject_GetAttrString(self->wrapped_object, "__module__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWebTransactionWrapper_get_wrapped(
        NRWebTransactionWrapperObject *self, void *closure)
{
    Py_INCREF(self->wrapped_object);
    return self->wrapped_object;
}
 
/* ------------------------------------------------------------------------- */

static PyObject *NRWebTransactionWrapper_descr_get(PyObject *function,
                                                  PyObject *object,
                                                  PyObject *type)
{
    if (object == Py_None)
        object = NULL;

    return PyMethod_New(function, object, type);
}

/* ------------------------------------------------------------------------- */

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

static PyGetSetDef NRWebTransactionWrapper_getset[] = {
    { "__name__",           (getter)NRWebTransactionWrapper_get_name,
                            NULL, 0 },
    { "__module__",         (getter)NRWebTransactionWrapper_get_module,
                            NULL, 0 },
    { "__wrapped__",        (getter)NRWebTransactionWrapper_get_wrapped,
                            NULL, 0 },
    { NULL },
};

PyTypeObject NRWebTransactionWrapper_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.WebTransactionWrapper", /*tp_name*/
    sizeof(NRWebTransactionWrapperObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRWebTransactionWrapper_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRWebTransactionWrapper_call, /*tp_call*/
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
    NRWebTransactionWrapper_getset, /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    NRWebTransactionWrapper_descr_get, /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)NRWebTransactionWrapper_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRWebTransactionWrapper_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRWebTransactionDecorator_new(PyTypeObject *type,
                                              PyObject *args, PyObject *kwds)
{
    NRWebTransactionDecoratorObject *self;

    self = (NRWebTransactionDecoratorObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->application = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRWebTransactionDecorator_init(NRWebTransactionDecoratorObject *self,
                                         PyObject *args, PyObject *kwds)
{
    PyObject *application = Py_None;

    static char *kwlist[] = { "application", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:WebTransactionDecorator",
                                     kwlist, &application)) {
        return -1;
    }

    if (application != Py_None &&
        Py_TYPE(application) != &NRApplication_Type &&
        !PyString_Check(application) && !PyUnicode_Check(application)) {
        PyErr_Format(PyExc_TypeError, "application argument must be None, "
                     "str, unicode, or application object, found type '%s'",
                     application->ob_type->tp_name);
        return -1;
    }

    Py_INCREF(application);
    Py_XDECREF(self->application);
    self->application = application;

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRWebTransactionDecorator_dealloc(
        NRWebTransactionDecoratorObject *self)
{
    Py_XDECREF(self->application);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWebTransactionDecorator_call(
        NRWebTransactionDecoratorObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;

    static char *kwlist[] = { "wrapped", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:WebTransactionDecorator",
                                     kwlist, &wrapped_object)) {
        return NULL;
    }

    return PyObject_CallFunctionObjArgs(
            (PyObject *)&NRWebTransactionWrapper_Type,
            wrapped_object, self->application, NULL);
}

/* ------------------------------------------------------------------------- */

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

PyTypeObject NRWebTransactionDecorator_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.WebTransactionDecorator", /*tp_name*/
    sizeof(NRWebTransactionDecoratorObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRWebTransactionDecorator_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRWebTransactionDecorator_call, /*tp_call*/
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
    (initproc)NRWebTransactionDecorator_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRWebTransactionDecorator_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

/*
 * vim: set cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
