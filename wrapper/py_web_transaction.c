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

#if 0
    const char *script_long_fragment = "<script>var NREUMQ=[];"
            "NREUMQ.push([\"mark\",\"firstbyte\",new Date().getTime()]);"
            "(function(){var d=document;var e=d.createElement(\"script\");"
            "e.type=\"text/javascript\";e.async=true;e.src=\"%s\";"
            "var s=d.getElementsByTagName(\"script\")[0];"
            "s.parentNode.insertBefore(e,s);})();"
            "</script>";
#endif

    /*
     * XXX Add 'http://' in start of URL for episode file as not
     * currently being passed through by PHP agent code properly.
     */

    const char *script_long_fragment = "<script>var NREUMQ=[];"
            "NREUMQ.push([\"mark\",\"firstbyte\",new Date().getTime()]);"
            "(function(){var d=document;var e=d.createElement(\"script\");"
            "e.type=\"text/javascript\";e.async=true;e.src=\"http://%s\";"
            "var s=d.getElementsByTagName(\"script\")[0];"
            "s.parentNode.insertBefore(e,s);})();"
            "</script>";

    char const *license_key = NULL;
    char const *beacon = NULL;
    char const *browser_key = NULL;
    char const *episodes_url = NULL;
    int application_id = 0;

    if (!self->transaction)
        return PyString_FromString("");

    if (self->transaction_state != NR_TRANSACTION_STATE_RUNNING)
        return PyString_FromString("");

    /*
     * XXX This needs to be updated when PHP agent code is updated to
     * pass back episodes_url and load_episodes_file flag. Just check
     * for beacon being set for now.
     */

    license_key = self->application->application->license_key;
    beacon = self->application->application->beacon;
    browser_key = self->application->application->browser_key;
    episodes_url = self->application->application->episodes_file;
    application_id = self->application->application->application_id;

    if (!beacon)
        return PyString_FromString("");

    self->transaction->has_returned_browser_timing_header = 1;

    if (episodes_url && *episodes_url)
        return PyString_FromFormat(script_long_fragment, episodes_url);
    else
        return PyString_FromString(script_short_fragment);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRWebTransaction_footer(NRTransactionObject *self,
                                         PyObject *args)
{
    const char *script_fragment = "<script type=\"text/javascript\" "
            "charset=\"utf-8\">NREUMQ.push([\"nrf2\",\"%s\",\"%s\",%d,"
            "\"%s\",%ld,%ld])</script>";

    char const *license_key = NULL;
    char const *beacon = NULL;
    char const *browser_key = NULL;
    int application_id = 0; 

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

    if (!self->transaction->has_returned_browser_timing_header)
        return PyString_FromString("");

    license_key = self->application->application->license_key;
    beacon = self->application->application->beacon;
    browser_key = self->application->application->browser_key;
    application_id = self->application->application->application_id;

    if (!license_key || !beacon || !browser_key)
        return PyString_FromString("");

    transaction_name = NRUtilities_ObfuscateTransactionName(
            self->transaction->path, license_key);

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
    total_duration_usec = stop_time_usec - queue_time_usec;

    result = PyString_FromFormat(script_fragment, beacon, browser_key,
                                 application_id,
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

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
