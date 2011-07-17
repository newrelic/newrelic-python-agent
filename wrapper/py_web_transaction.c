/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_web_transaction.h"

#include "globals.h"

#include "py_settings.h"
#include "py_utilities.h"

#include "structmember.h"

/* ------------------------------------------------------------------------- */

static int NRWebTransaction_init(NRTransactionObject *self, PyObject *args,
                                 PyObject *kwds)
{
    NRApplicationObject *application = NULL;
    PyObject *environ = NULL;

    PyObject *enabled = NULL;
    PyObject *newargs = NULL;
    PyObject *object = NULL;

    PyObject *module = NULL;
    PyObject *dict = NULL;
    PyObject *function = NULL;
    PyObject *result = NULL;

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
        const char *script_name = NULL;
        const char *path_info = NULL;

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

        if (self->transaction->path == 0) {
            object = PyDict_GetItemString(environ, "REQUEST_URI");

            if (object && PyString_Check(object)) {
                self->transaction->path_type = NR_PATH_TYPE_URI;
                self->transaction->path = nrstrdup(PyString_AsString(object));
                self->transaction->realpath = nrstrdup(self->transaction->path);
            }
        }

        if (self->transaction->path == 0) {
            self->transaction->path_type = NR_PATH_TYPE_UNKNOWN;
            self->transaction->path = nrstrdup("<unknown>");
            self->transaction->realpath = nrstrdup(self->transaction->path);
        }

        /*
         * See if the WSGI environ dictionary includes the
         * special 'X-Queue-Start' HTTP header. This
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
         *
	 * Note that mod_wsgi 4.0 sets its own distinct variable
	 * called mod_wsgi.queue_start so that not necessary to
	 * enable and use mod_headers to add X-Queue-Start. So
	 * also check for that, but give priority to the
	 * explicitly added header in case that header was added
	 * in front end server to Apache instead although for that
         * case they should be using X-Request-Start which do not
         * support here yet as PHP agent core doesn't have a way
         * of tracking front end web server time.
         */

        self->transaction->http_x_request_start = 0;

        object = PyDict_GetItemString(environ, "HTTP_X_QUEUE_START");

        if (object && PyString_Check(object)) {
            const char *s = PyString_AsString(object);
            if (s[0] == 't' && s[1] == '=' ) {
                self->transaction->http_x_request_start = (int64_t)strtoll(
                        s+2, 0, 0);
            }
        }

        if (self->transaction->http_x_request_start == 0) {
            object = PyDict_GetItemString(environ, "mod_wsgi.queue_start");

            if (object && PyString_Check(object)) {
                const char *s = PyString_AsString(object);
                self->transaction->http_x_request_start = (int64_t)strtoll(
                            s, 0, 0);
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
         * Check whether web transaction being flagged as to be
         * ignored for purposes of apdex. That is still count the
         * transaction but don't use it in apdex metrics.
         */

        self->transaction->ignore_apdex = 0;

        object = PyDict_GetItemString(environ, "newrelic.ignore_apdex");

        if (object) {
            if (PyBool_Check(object)) {
                if (object == Py_True)
                    self->transaction->ignore_apdex = 1;
            }
            else if (PyString_Check(object)) {
                const char *value;

                value = PyString_AsString(object);

                if (!strcasecmp(value, "on"))
                    self->transaction->ignore_apdex = 1;
            }
        }

        /*
         * Create a copy of the WSGI environ for the request
         * parameters. We don't just reference the original
         * environ dictionary as WSGI middleware may change the
         * content in place and so data could end up being
         * different to what it was at start of the request.
         */

#if 0
        /*
         * XXX Not supposed to be doing this. Should only be
         * copying a split up QUERY_STRING.
         */

        PyDict_Update(self->request_parameters, environ);
#endif

        module = PyImport_ImportModule("urlparse");

        if (module) {
            dict = PyModule_GetDict(module);

            function = PyDict_GetItemString(dict, "parse_qs");
            Py_XINCREF(function);

            Py_DECREF(module);
        }

        if (!function) {
            module = PyImport_ImportModule("cgi");

            if (module) {
                dict = PyModule_GetDict(module);

                function = PyDict_GetItemString(dict, "parse_qs");
                Py_XINCREF(function);

                Py_DECREF(module);
            }
        }

        if (function) {
            object = PyDict_GetItemString(environ, "QUERY_STRING");

            if (object) {
                result = PyObject_CallFunctionObjArgs(function, object,
                                                      Py_True, NULL);

                /* Shouldn't ever fail. */

                if (result) {
                    PyDict_Update(self->request_parameters, result);
                    Py_DECREF(result);
                }
                else
                    PyErr_Clear();
            }
        }

        Py_XDECREF(function);
    }

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWebTransaction_header(NRTransactionObject *self,
                                         PyObject *args)
{
    const char *script_fragment = "<script type=\"text/javascript\">"
            "var NREUMQ=[];NREUMQ.push([\"mark\",\"firstbyte\","
            "new Date().getTime()])</script>";

    if (!self->transaction)
        return PyString_FromString("");

    if (self->transaction_state != NR_TRANSACTION_STATE_RUNNING)
        return PyString_FromString("");

    if (self->transaction->ignore)
        return PyString_FromString("");

    if (!self->application->application->episodes_url)
        return PyString_FromString("");

    self->transaction->has_autorum_browser_timing_header = 1;

    return PyString_FromString(script_fragment);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWebTransaction_footer(NRTransactionObject *self,
                                         PyObject *args)
{
    const char *script_short_fragment = "<script type=\"text/javascript\">"
            "NREUMQ.push([\"nrf2\",\"%s\",\"%s\",%d,\"%s\",%ld,%ld,"
            "new Date().getTime()])</script>";

    const char *script_long_fragment = "<script type=\"text/javascript\">"
            "(function(){var d=document;var e=d.createElement(\"script\");"
            "e.type=\"text/javascript\";e.async=true;e.src=\"%s\";"
            "var s=d.getElementsByTagName(\"script\")[0];"
            "s.parentNode.insertBefore(e,s);})();NREUMQ.push([\"nrf2\","
            "\"%s\",\"%s\",%d,\"%s\",%ld,%ld,new Date().getTime()])</script>";

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

    if (!self->transaction->has_autorum_browser_timing_header)
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

    if (!self->application->application->load_episodes_file) {
        result = PyString_FromFormat(script_short_fragment,
                self->application->application->beacon,
                self->application->application->browser_key,
                self->application->application->application_id,
                PyString_AsString(transaction_name),
                (long)(queue_duration_usec/1000),
                (long)(total_duration_usec/1000));
    }
    else {
        result = PyString_FromFormat(script_long_fragment,
                self->application->application->episodes_url,
                self->application->application->beacon,
                self->application->application->browser_key,
                self->application->application->application_id,
                PyString_AsString(transaction_name),
                (long)(queue_duration_usec/1000),
                (long)(total_duration_usec/1000));
    }

    Py_DECREF(transaction_name);

    self->path_frozen = 1;

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

static PyObject *NRWSGIApplicationIterable_new(PyTypeObject *type,
                                               PyObject *args,
                                               PyObject *kwds)
{
    NRWSGIApplicationIterableObject *self;

    self = (NRWSGIApplicationIterableObject *)type->tp_alloc(type, 0);

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

static int NRWSGIApplicationIterable_init(NRWSGIApplicationIterableObject *self,
                                          PyObject *args, PyObject *kwds)
{
    PyObject *application = NULL;
    PyObject *wrapped_object = NULL;
    PyObject *application_args = NULL;

    PyObject *app_name = NULL;

    PyObject *environ = NULL;
    PyObject *start_response = NULL;

    PyObject *instance_method = NULL;
    PyObject *method_args = NULL;
    PyObject *method_result = NULL;

    int i = 0;

    static char *kwlist[] = { "application", "wrapped", "args", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds,
                                     "O!OO!:WSGIApplicationIterable",
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

    if (!PyDict_Check(environ)) {
        PyErr_SetString(PyExc_ValueError, "environ expect to be a dict");
        return -1;
    }

    app_name = PyDict_GetItemString(environ, "newrelic.app_name");

    /*
     * XXX So far assuming constructor not called twice. Also
     * not checking that creation of transaction failing.
     */

    if (app_name) {
        PyObject *func_args = NULL;

        PyObject *override = NULL;

        if (!PyString_Check(app_name) && !PyUnicode_Check(app_name)) {
            PyErr_SetString(PyExc_ValueError,
                    "newrelic.app_name expected to be string or Unicode");
            return -1;
        }

        func_args = PyTuple_Pack(1, app_name);

        override = NRApplication_Singleton(func_args, NULL);

        if (!override) {
            Py_DECREF(func_args);
            return -1;
        }

        self->transaction = PyObject_CallFunctionObjArgs((PyObject *)
                &NRWebTransaction_Type, override, environ, NULL);

        Py_DECREF(func_args);
        Py_DECREF(override);
    }
    else {
        self->transaction = PyObject_CallFunctionObjArgs((PyObject *)
                &NRWebTransaction_Type, self->application, environ, NULL);
    }

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

        instance_method = PyObject_GetAttrString(self->transaction,
                                                 "__exit__");

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

static void NRWSGIApplicationIterable_dealloc(
        NRWSGIApplicationIterableObject *self)
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

static PyObject *NRWSGIApplicationIterable_iter(
        NRWSGIApplicationIterableObject *self)
{
    self->iterable = PyObject_GetIter(self->result);

    Py_INCREF(self);
    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWSGIApplicationIterable_iternext(
        NRWSGIApplicationIterableObject *self)
{
    return PyIter_Next(self->iterable);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWSGIApplicationIterable_close(
        NRWSGIApplicationIterableObject *self, PyObject *args)
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
            wrapped_result = PyObject_CallFunctionObjArgs(wrapped_method,
                                                          NULL);

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

static PyObject *NRWSGIApplicationIterable_start(
        NRWSGIApplicationIterableObject *self, PyObject *args)
{
    PyObject *status_line = NULL;
    PyObject *headers = NULL;
    PyObject *exc_info = NULL;

    long status_as_int = 0;
    PyObject *status = NULL;

    if (!PyArg_ParseTuple(args, "O!O!|O:start_response", &PyString_Type,
                          &status_line, &PyList_Type, &headers, &exc_info)) {
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

static PyMethodDef NRWSGIApplicationIterable_methods[] = {
    { "close",              (PyCFunction)NRWSGIApplicationIterable_close,
                            METH_NOARGS, 0 },
    { "start_response",     (PyCFunction)NRWSGIApplicationIterable_start,
                            METH_VARARGS, 0 },
    { NULL, NULL }
};

PyTypeObject NRWSGIApplicationIterable_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.WSGIApplicationIterable", /*tp_name*/
    sizeof(NRWSGIApplicationIterableObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRWSGIApplicationIterable_dealloc, /*tp_dealloc*/
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
    (getiterfunc)NRWSGIApplicationIterable_iter, /*tp_iter*/
    (iternextfunc)NRWSGIApplicationIterable_iternext, /*tp_iternext*/
    NRWSGIApplicationIterable_methods, /*tp_methods*/
    0,                      /*tp_members*/
    0,                      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)NRWSGIApplicationIterable_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRWSGIApplicationIterable_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRWSGIApplicationWrapper_new(
        PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    NRWSGIApplicationWrapperObject *self;

    self = (NRWSGIApplicationWrapperObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->dict = NULL;
    self->next_object = NULL;
    self->last_object = NULL;
    self->application = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRWSGIApplicationWrapper_init(
        NRWSGIApplicationWrapperObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;

    PyObject *application = Py_None;

    PyObject *object = NULL;

    static char *kwlist[] = { "wrapped", "application", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O|O:WSGIApplicationWrapper",
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

        NRSettingsObject *settings = NULL;

        settings = (NRSettingsObject *)NRSettings_Singleton();

        if (application == Py_None) {
            application = PyString_FromString(settings->app_name);
            func_args = PyTuple_Pack(1, application);
            Py_DECREF(application);
        }
        else
            func_args = PyTuple_Pack(1, application);

        application = NRApplication_Singleton(func_args, NULL);

        Py_DECREF(settings);

        Py_DECREF(func_args);
    }
    else
        Py_INCREF(application);

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

    Py_XDECREF(self->application);
    self->application = application;

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRWSGIApplicationWrapper_dealloc(
        NRWSGIApplicationWrapperObject *self)
{
    Py_XDECREF(self->dict);

    Py_XDECREF(self->next_object);
    Py_XDECREF(self->last_object);

    Py_XDECREF(self->application);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWSGIApplicationWrapper_call(
        NRWSGIApplicationWrapperObject *self, PyObject *args, PyObject *kwds)
{
    return PyObject_CallFunctionObjArgs((PyObject *)
            &NRWSGIApplicationIterable_Type, self->application,
            self->next_object, args, NULL);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWSGIApplicationWrapper_get_next(
        NRWSGIApplicationWrapperObject *self, void *closure)
{
    if (!self->next_object) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    Py_INCREF(self->next_object);
    return self->next_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWSGIApplicationWrapper_get_last(
        NRWSGIApplicationWrapperObject *self, void *closure)
{
    if (!self->last_object) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    Py_INCREF(self->last_object);
    return self->last_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWSGIApplicationWrapper_get_marker(
        NRWSGIApplicationWrapperObject *self, void *closure)
{
    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWSGIApplicationWrapper_get_module(
        NRWSGIApplicationWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    return PyObject_GetAttrString(self->last_object, "__module__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWSGIApplicationWrapper_get_name(
        NRWSGIApplicationWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    return PyObject_GetAttrString(self->last_object, "__name__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWSGIApplicationWrapper_get_doc(
        NRWSGIApplicationWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    return PyObject_GetAttrString(self->last_object, "__doc__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWSGIApplicationWrapper_get_dict(
        NRWSGIApplicationWrapperObject *self)
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

static PyObject *NRWSGIApplicationWrapper_getattro(
        NRWSGIApplicationWrapperObject *self, PyObject *name)
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

static int NRWSGIApplicationWrapper_setattro(
        NRWSGIApplicationWrapperObject *self, PyObject *name, PyObject *value)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return -1;
    }

    return PyObject_SetAttr(self->last_object, name, value);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWSGIApplicationWrapper_descr_get(PyObject *function,
                                                PyObject *object,
                                                PyObject *type)
{
    if (object == Py_None)
        object = NULL;

    return PyMethod_New(function, object, type);
}

/* ------------------------------------------------------------------------- */

static PyGetSetDef NRWSGIApplicationWrapper_getset[] = {
    { "__next_object__",    (getter)NRWSGIApplicationWrapper_get_next,
                            NULL, 0 },
    { "__last_object__",    (getter)NRWSGIApplicationWrapper_get_last,
                            NULL, 0 },
    { "__newrelic__",       (getter)NRWSGIApplicationWrapper_get_marker,
                            NULL, 0 },
    { "__module__",         (getter)NRWSGIApplicationWrapper_get_module,
                            NULL, 0 },
    { "__name__",           (getter)NRWSGIApplicationWrapper_get_name,
                            NULL, 0 },
    { "__doc__",            (getter)NRWSGIApplicationWrapper_get_doc,
                            NULL, 0 },
    { "__dict__",           (getter)NRWSGIApplicationWrapper_get_dict,
                            NULL, 0 },
    { NULL },
};

PyTypeObject NRWSGIApplicationWrapper_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.WSGIApplicationWrapper", /*tp_name*/
    sizeof(NRWSGIApplicationWrapperObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRWSGIApplicationWrapper_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRWSGIApplicationWrapper_call, /*tp_call*/
    0,                      /*tp_str*/
    (getattrofunc)NRWSGIApplicationWrapper_getattro, /*tp_getattro*/
    (setattrofunc)NRWSGIApplicationWrapper_setattro, /*tp_setattro*/
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
    NRWSGIApplicationWrapper_getset, /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    NRWSGIApplicationWrapper_descr_get, /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    offsetof(NRWSGIApplicationWrapperObject, dict), /*tp_dictoffset*/
    (initproc)NRWSGIApplicationWrapper_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRWSGIApplicationWrapper_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRWSGIApplicationDecorator_new(PyTypeObject *type,
                                              PyObject *args, PyObject *kwds)
{
    NRWSGIApplicationDecoratorObject *self;

    self = (NRWSGIApplicationDecoratorObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->application = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRWSGIApplicationDecorator_init(
        NRWSGIApplicationDecoratorObject *self,
                                         PyObject *args, PyObject *kwds)
{
    PyObject *application = Py_None;

    static char *kwlist[] = { "application", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:WSGIApplicationDecorator",
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

static void NRWSGIApplicationDecorator_dealloc(
        NRWSGIApplicationDecoratorObject *self)
{
    Py_XDECREF(self->application);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWSGIApplicationDecorator_call(
        NRWSGIApplicationDecoratorObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;

    static char *kwlist[] = { "wrapped", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:WSGIApplicationDecorator",
                                     kwlist, &wrapped_object)) {
        return NULL;
    }

    return PyObject_CallFunctionObjArgs(
            (PyObject *)&NRWSGIApplicationWrapper_Type,
            wrapped_object, self->application, NULL);
}

/* ------------------------------------------------------------------------- */

PyTypeObject NRWSGIApplicationDecorator_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.WSGIApplicationDecorator", /*tp_name*/
    sizeof(NRWSGIApplicationDecoratorObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRWSGIApplicationDecorator_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRWSGIApplicationDecorator_call, /*tp_call*/
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
    (initproc)NRWSGIApplicationDecorator_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRWSGIApplicationDecorator_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

/*
 * vim: set cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
