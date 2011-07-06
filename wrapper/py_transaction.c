/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_transaction.h"

#include "py_settings.h"
#include "py_utilities.h"

#include "globals.h"
#include "logging.h"

#include "application.h"
#include "genericobject.h"
#include "harvest.h"
#include "web_transaction.h"

#include "metric_table.h"
#include "daemon_protocol.h"

#include "pythread.h"

/* ------------------------------------------------------------------------- */

static int NRTransaction_tls_key = 0;
static int NRTransaction_cls_key = 0;
static nrthread_mutex_t NRTransaction_exit_mutex;

/* ------------------------------------------------------------------------- */

PyObject *NRTransaction_CurrentTransaction()
{
    PyObject *modules = NULL;
    PyObject *module = NULL;

    PyObject *result = NULL;

    if (!NRTransaction_tls_key)
        return NULL;

    /*
     * Have to check whether might be using greenlet
     * coroutines first instead of normal threading.
     */

    modules = PyImport_GetModuleDict();

    module = PyDict_GetItemString(modules, "greenlet");

    if (module) {
        PyObject *dict = NULL;
        PyObject *func = NULL;

        dict = PyModule_GetDict(module);

        func = PyDict_GetItemString(dict, "getcurrent");

        if (func) {
            PyObject *current = NULL;

            current = PyObject_CallFunctionObjArgs(func, NULL);

            if (current) {
                PyObject *storage = NULL;

                storage = (PyObject *)PyThread_get_key_value(
                        NRTransaction_cls_key);

                if (storage) {
                    PyObject *handle = NULL;

                    handle = PyDict_GetItem(storage, current);

                    result = (PyObject *)PyCObject_AsVoidPtr(handle);
                }
            }
            else
                PyErr_Clear();

            Py_XDECREF(current);
        }
    }

    /*
     * If wasn't held in coroutine local storage then we
     * need to look in the normal thread local storage.
     */

    if (!result)
        result = (PyObject *)PyThread_get_key_value(NRTransaction_tls_key);

    return result;
}

/* ------------------------------------------------------------------------- */

PyObject *NRTransaction_PushTransaction(PyObject *transaction)
{
    PyObject *modules = NULL;
    PyObject *module = NULL;

    /*
     * Ensure transaction has not already been setup for this
     * thread. This means we preclude nested web transactions
     * from occuring. In the case of where coroutines are being
     * used, this situation still shouldn't occur and we will
     * fall through to looking at the coroutine local storage
     * instead.
     */

    if (PyThread_get_key_value(NRTransaction_tls_key)) {
        PyErr_SetString(PyExc_RuntimeError, "thread local already set");
        return NULL;
    }

    /*
     * Check now whether we are running as a coroutine using the
     * greenlet library extension instead of a normal thread.
     */

    modules = PyImport_GetModuleDict();

    module = PyDict_GetItemString(modules, "greenlet");

    if (module) {
        PyObject *dict = NULL;
        PyObject *func = NULL;

        dict = PyModule_GetDict(module);

        func = PyDict_GetItemString(dict, "getcurrent");

        if (func) {
            PyObject *current = NULL;

            current = PyObject_CallFunctionObjArgs(func, NULL);

            if (current) {
                PyObject *storage = NULL;
                PyObject *handle = NULL;

                storage = (PyObject *)PyThread_get_key_value(
                        NRTransaction_cls_key);

                if (!storage) {
                    storage = PyDict_New();
                    PyThread_set_key_value(NRTransaction_cls_key, storage);
                }
                else {
                    if (PyDict_GetItem(storage, current)) {
                        PyErr_SetString(PyExc_RuntimeError,
                                "coroutine local already set");

                        Py_DECREF(current);
                        Py_DECREF(module);

                        return NULL;
                    }
                }

                /*
                 * We store the transaction in a C object as
                 * we don't want a reference count as that
                 * would prevent exit being called from
                 * destructor of transaction if not called
                 * prior to that put as should be the case.
                 */

                handle = PyCObject_FromVoidPtr(transaction, NULL);

                PyDict_SetItem(storage, current, handle);

                Py_DECREF(handle);

                /*
                 * Set flag in transaction so we know that we
                 * are using coroutines for this transaction.
                 */

                ((NRTransactionObject *)transaction)->coroutines = 1;

                /*
                 * NULL out transaction pointer so when we
                 * fall through below we don't also store it
                 * under normal thread local storage.
                 */

                transaction = NULL;
            }
            else
                PyErr_Clear();

            Py_XDECREF(current);
        }
    }

    /*
     * If not stored as coroutine local storage then store as
     * normal thread local storage.
     */

    if (transaction)
        PyThread_set_key_value(NRTransaction_tls_key, transaction);

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

PyObject *NRTransaction_PopTransaction(PyObject *transaction)
{
    PyObject *modules = NULL;
    PyObject *module = NULL;

    PyObject *existing = NULL;

    /*
     * Have to check whether might be using greenlet
     * coroutines first instead of normal threading.
     */

    modules = PyImport_GetModuleDict();

    module = PyDict_GetItemString(modules, "greenlet");

    if (module) {
        PyObject *dict = NULL;
        PyObject *func = NULL;

        dict = PyModule_GetDict(module);

        func = PyDict_GetItemString(dict, "getcurrent");

        if (func) {
            PyObject *current = NULL;

            current = PyObject_CallFunctionObjArgs(func, NULL);

            if (current) {
                PyObject *storage = NULL;

                storage = (PyObject *)PyThread_get_key_value(
                        NRTransaction_cls_key);

                if (storage) {
                    PyObject *handle = NULL;

                    handle = PyDict_GetItem(storage, current);

                    existing = (PyObject *)PyCObject_AsVoidPtr(handle);

                    if (existing != transaction) {
                        PyErr_SetString(PyExc_RuntimeError,
                                "coroutine local doesn't match");

                        Py_DECREF(current);
                        Py_DECREF(module);

                        return NULL;
                    }

                    PyDict_DelItem(storage, current);

                    /*
                     * NULL out transaction pointer so when we
                     * fall through below we don't also remove it
                     * from normal thread local storage.
                     */

                    transaction = NULL;
                }
            }
            else
                PyErr_Clear();

            Py_XDECREF(current);
        }
    }

    /*
     * If wasn't held in coroutine local storage then we
     * need to clear it from the normal thread local storage.
     */

    if (transaction) {
        existing = (PyObject *)PyThread_get_key_value(NRTransaction_tls_key);

        if (!existing) {
            PyErr_SetString(PyExc_RuntimeError, "thread local not set");
            return NULL;
        }

        if (existing != transaction) {
            PyErr_SetString(PyExc_RuntimeError, "thread local doesn't match");
            return NULL;
        }

        PyThread_delete_key_value(NRTransaction_tls_key);
    }

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRTransaction_new(PyTypeObject *type, PyObject *args,
                                   PyObject *kwds)
{
    NRTransactionObject *self;

    NRSettingsObject *settings = NULL;

    /*
     * Initialise thread local storage and coroutine local
     * storage if necessary. Startup the harvest thread. Do this
     * here rather than init method as technically the latter
     * may not be called.
     *
     * TODO Also initialise mutex for __exit__() function
     * used to get around thread safety issues in inner agent
     * code. See https://www.pivotaltracker.com/projects/154789.
     */

    if (!NRTransaction_tls_key) {
        NRTransaction_tls_key = PyThread_create_key();
        NRTransaction_cls_key = PyThread_create_key();

        nrthread_mutex_init(&NRTransaction_exit_mutex, NULL);

#ifdef NR_AGENT_DEBUG
        nr__log(LOG_VERBOSEDEBUG, "start harvest thread");
#endif
        nr__create_harvest_thread();
    }

    /*
     * Allocate the transaction object and initialise it as per
     * normal.
     */

    self = (NRTransactionObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->application = NULL;
    self->transaction = NULL;
    self->transaction_errors = NULL;

    self->transaction_state = NR_TRANSACTION_STATE_PENDING;

    self->path_frozen = 0;

    self->request_parameters = PyDict_New();
    self->custom_parameters = PyDict_New();

    self->capture_params = nr_per_process_globals.enable_params;

    settings = (NRSettingsObject *)NRSettings_Singleton();

    self->ignored_params = PyObject_CallFunctionObjArgs(
                (PyObject *)&PyList_Type, settings->ignored_params, NULL);

    self->coroutines = 0;

    Py_DECREF(settings);

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRTransaction_init(NRTransactionObject *self, PyObject *args,
                              PyObject *kwds)
{
    NRApplicationObject *application = NULL;

    NRSettingsObject *settings = NULL;

    PyObject *enabled = NULL;

    nrdaemon_t *dconn = &nr_per_process_globals.nrdaemon;

    int retry_connection = 0;

    static char *kwlist[] = { "application", "enabled", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O!|O!:Transaction",
                                     kwlist, &NRApplication_Type,
                                     &application, &PyBool_Type, &enabled)) {
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
     * We already tried to initiate the connection when the
     * application object was created. If that did not connect
     * then we try and restart the connection at this point.
     */

    nrthread_mutex_lock(&application->application->lock);
    if (application->application->agent_run_id == 0)
        retry_connection = 1;
    nrthread_mutex_unlock(&application->application->lock);

    if (retry_connection) {
        nr__start_communication(dconn, application->application,
                nr_per_process_globals.env, 0);
    }

    /*
     * Cache reference to the application object instance as we
     * will need that latter when doing some work arounds for
     * lack of thread safety in agent library client code. The
     * application object also holds the enabled flag for the
     * application. If the application isn't enabled then we
     * don't actually do anything but still create objects as
     * standins so any code still runs. Note though that the
     * global agent application monitoring flag trumps
     * everything and if that is disabled doesn't matter what
     * other settings are.
     */

    self->application = application;
    Py_INCREF(self->application);

    settings = (NRSettingsObject *)NRSettings_Singleton();

    if (settings->monitor_mode &&
        (enabled == Py_True || (!enabled && application->enabled))) {
        self->transaction = nr_web_transaction__allocate();

        self->transaction->path_type = NR_PATH_TYPE_UNKNOWN;
        self->transaction->path = NULL;
        self->transaction->realpath = NULL;

        /*
	 * If we have not connected to the local daemon as yet
	 * then we mark the transaction as ignored because we
	 * will not have the proper server side configuration
	 * settings available to determine how to handle the
	 * transaction.
         */

        nrthread_mutex_lock(&application->application->lock);
        if (application->application->agent_run_id == 0)
            self->transaction->ignore = 1;
        nrthread_mutex_unlock(&application->application->lock);
    }

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRTransaction_exit(NRTransactionObject *self,
                                        PyObject *args);

static void NRTransaction_dealloc(NRTransactionObject *self)
{
    /*
     * If transaction still running when this object is being
     * destroyed then force call of exit method to finalise the
     * transaction. Note that we call the exit method directly
     * rather than looking it up from the object because doing
     * the later causes the object to be destroyed twice. This
     * would be a problem if a derived class overrides the exit
     * method, but this in practice should never occur.
     */

    if (self->transaction_state == NR_TRANSACTION_STATE_RUNNING) {
        PyObject *args = NULL;
        PyObject *result = NULL;

        PyObject *type = NULL;
        PyObject *value = NULL;
        PyObject *traceback = NULL;

        int have_error = PyErr_Occurred() ? 1 : 0;

        if (have_error)
            PyErr_Fetch(&type, &value, &traceback);

        args = PyTuple_Pack(3, Py_None, Py_None, Py_None);

        result = NRTransaction_exit(self, args);

        if (!result) {
            /*
             * XXX The error should really be logged against the
             * exit method, but we don't have an handle to it as
             * a Python object. Only way around that would be to
             * get the method from the type dictionary.
             */

            PyErr_WriteUnraisable((PyObject *)self);
        }
        else
            Py_DECREF(result);

        if (have_error)
            PyErr_Restore(type, value, traceback);

        Py_DECREF(args);
    }

    Py_DECREF(self->ignored_params);

    Py_DECREF(self->custom_parameters);
    Py_DECREF(self->request_parameters);

    Py_XDECREF(self->application);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRTransaction_enter(NRTransactionObject *self,
                                     PyObject *args)
{
    nr_node_header *save;

    PyObject *result = NULL;

    if (!self->application) {
        PyErr_SetString(PyExc_TypeError, "transaction not initialized");
        return NULL;
    }

    if (self->transaction_state == NR_TRANSACTION_STATE_STOPPED) {
        PyErr_SetString(PyExc_RuntimeError, "transaction already completed");
        return NULL;
    }

    if (self->transaction_state == NR_TRANSACTION_STATE_RUNNING) {
        PyErr_SetString(PyExc_RuntimeError, "transaction already active");
        return NULL;
    }

    self->transaction_state = NR_TRANSACTION_STATE_RUNNING;

    /*
     * Save away the current transaction object into thread
     * local storage so that can easily access the current
     * transaction later on when creating traces without the
     * need to have a handle to the original transaction.
     */

    result = NRTransaction_PushTransaction((PyObject *)self);

    if (!result)
        return NULL;

    Py_DECREF(result);

    /*
     * If application was not enabled and so we are running
     * as a dummy transaction then return without actually
     * doing anything.
     */

    if (!self->transaction) {
        Py_INCREF(self);
        return (PyObject *)self;
    }

    /*
     * Start timing for the current transaction.
     */

    nr_node_header__record_starttime_and_push_current(
            (nr_node_header *)self->transaction, &save);

    Py_INCREF(self);
    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRTransaction_exit(NRTransactionObject *self,
                                    PyObject *args)
{
    int keep_wt = 0;

    nrapp_t *application;

    PyObject *type = NULL;
    PyObject *value = NULL;
    PyObject *traceback = NULL;

    PyObject *result = NULL;

    NRSettingsObject *settings = NULL;

    if (!PyArg_ParseTuple(args, "OOO:__exit__", &type, &value, &traceback))
        return NULL;

    if (self->transaction_state != NR_TRANSACTION_STATE_RUNNING) {
        PyErr_SetString(PyExc_RuntimeError, "transaction not active");
        return NULL;
    }

    /*
     * Remove the reference to the transaction from thread
     * local storage.
     */

    result = NRTransaction_PopTransaction((PyObject *)self);

    if (!result)
        return NULL;

    Py_DECREF(result);

    /*
     * If application was not enabled and so we are running
     * as a dummy transaction then return without actually
     * doing anything.
     */

    if (!self->transaction) {
        self->transaction_state = NR_TRANSACTION_STATE_STOPPED;

        Py_INCREF(Py_None);
        return Py_None;
    }

    /*
     * Treat any exception passed in as being unhandled and
     * record details of exception against the transaction.
     * It is presumed that original error was not registered in
     * this context and so do not need to restore it when any
     * error here is cleared.
     */

    if (type != Py_None && value != Py_None && traceback != Py_None) {
        PyObject *object = NULL;

        object = PyObject_GetAttrString((PyObject *)self, "notice_error");

        if (object) {
            PyObject *args = NULL;
            PyObject *result = NULL;

            args = PyTuple_Pack(3, type, value, traceback);
            result = PyObject_Call(object, args, NULL);

            Py_DECREF(args);
            Py_DECREF(object);
            Py_XDECREF(result);
        }
    }

    /* Stop the current transaction and then distill data. */

    nr_node_header__record_stoptime_and_pop_current(
            (nr_node_header *)self->transaction, NULL);

    /*
     * TODO Switching what the current application is here is a
     * PITA. The following harvest function should accept the
     * application as a parameter rather than internally
     * consulting the global variable referencing the current
     * application. See more details on Pivotal Tracker at
     * https://www.pivotaltracker.com/story/show/8953159. We use
     * a local mutex to prevent multiple threads running
     * through this critical section at this point. We release
     * the Python GIL at this point just in case inner agent
     * code were ever to take a long time or changed in some
     * way that it may block because of forced socket operations.
     * If that can never occur and processing of transaction
     * is always quick, then could just use Python GIL for the
     * purposes of excluding multiple threads from this section.
     */

    application = self->application->application;

    nrthread_mutex_lock(&NRTransaction_exit_mutex);

    /*
     * TODO The use of a global for transaction threshold in
     * PHP agent core is broken for multithreaded applications.
     * The problem being that the global needs to be switched
     * on each request to correspond to the value for the
     * associated application if apdex_f calculation being used
     * or fallback to integer value supplied in configuration
     * file if not. See more details on Pivotal Tracker at
     * https://www.pivotaltracker.com/story/show/12771611.
     * Note have have this workaround before lock application
     * because setting threshold from apdex against a specific
     * application grabs the application lock. If do it after
     * we have grabbed application lock it will deadlock as the
     * lock isn't recursive.
     */

    settings = (NRSettingsObject *)NRSettings_Singleton();

    if (settings->tracer_settings->transaction_threshold_is_apdex_f) {
        nr_per_process_globals.tt_threshold_is_apdex_f = 1;
#if 0
        /* Done in nr__switch_to_application(). */
        nr_initialize_global_tt_threshold_from_apdex(application);
#endif
    }
    else {
        nr_per_process_globals.tt_threshold_is_apdex_f = 0;
        nr_per_process_globals.tt_threshold =
                settings->tracer_settings->transaction_threshold;
    }

    nr__switch_to_application(application);

    /*
     * Must lock application here as the harvest thread uses
     * application lock when wanting to add sampler data to
     * the pending harvest metrics. Have to do this after the
     * switch to application or compound broken thread behaviour
     * in switching to application.
     */

    nrthread_mutex_lock(&application->lock);

    /*
     * XXX Can't release GIL here as trying to acquire it on
     * exit could deadlock where another thread is trying to
     * lock the exit mutex lock above.
     */

#if 0
    Py_BEGIN_ALLOW_THREADS
#endif

    keep_wt = nr__distill_web_transaction_into_harvest_data(
            self->transaction);

#if 0
    Py_END_ALLOW_THREADS
#endif

    /*
     * Only add request parameters and custom parameters into
     * web transaction object if the record is being kept due to
     * associated errors or because it is being tracked as a
     * slow transaction.
     *
     * XXX Note that we don't provide a way for whether request
     * parameters are recorded to be enabled on per request basis
     * using an API call as the PHP agent does. The Java and Ruby
     * agents don't have such an API call either.
     */

    if (keep_wt || self->transaction_errors != NULL) {
        if (self->capture_params) {
            PyObject *iter = NULL;
            PyObject *item = NULL;

            iter = PyObject_GetIter(self->ignored_params);

            if (iter) {
                while ((item = PyIter_Next(iter))) {
                    if (PyDict_DelItem(self->request_parameters, item) == -1)
                        PyErr_Clear();
                }

                Py_DECREF(iter);
            }
            else
                PyErr_Clear();

            /*
             * Make sure we always remove authorisation headers
             * to ensure that logins and passwords not sent back.
             *
             * XXX Not relevant now as not mean to pass whole
             * environ as request parameters anyway.
             */

#if 0
            PyDict_DelItemString(self->request_parameters,
                                 "HTTP_AUTHORIZATION");
            PyDict_DelItemString(self->request_parameters,
                                 "HTTP_PROXY_AUTHORIZATION");

            PyErr_Clear();
#endif

            NRUtilities_MergeDictIntoParams(self->transaction->params,
                                            "request_parameters",
                                            self->request_parameters);
        }

        NRUtilities_MergeDictIntoParams(self->transaction->params,
                                        "custom_parameters",
                                        self->custom_parameters);
    }

    /*
     * Process any errors associated with transaction and destroy
     * the transaction. Errors can be from unhandled exception
     * that propogated all the way back up the call stack, or one
     * which was explicitly attached to transaction by user code
     * but then supressed within the code.
     */

#if 0
    Py_BEGIN_ALLOW_THREADS
#endif

    nr_transaction_error__process_errors(self->transaction_errors,
            application->pending_harvest->metrics);
    nr__merge_errors_from_to(&self->transaction_errors,
            &application->pending_harvest->errors);
    nr__replace_pointers_in_errors(application->pending_harvest->errors);
    nr_metric_table__clear(self->transaction->in_progress_metrics);

    if (!keep_wt)
        nr_web_transaction__destroy(self->transaction);

#ifdef NR_AGENT_DEBUG
    nr__log(LOG_VERBOSEDEBUG, "pending_harvest->metrics->number = %d",
            application->pending_harvest->metrics->number);
    nr__log(LOG_VERBOSEDEBUG, "pending_harvest->slow_transactions = %d",
            !!application->pending_harvest->slow_transactions);
    nr__log(LOG_VERBOSEDEBUG, "pending_harvest->errors = %d",
            !!application->pending_harvest->errors);
#endif

#if 0
    Py_END_ALLOW_THREADS
#endif

    nrthread_mutex_unlock(&application->lock);

    nrthread_mutex_unlock(&NRTransaction_exit_mutex);

    self->transaction_state = NR_TRANSACTION_STATE_STOPPED;

    Py_DECREF(settings);

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRTransaction_notice_error(
        NRTransactionObject *self, PyObject *args, PyObject *kwds)
{
    nr_transaction_error *record;

    PyObject *type = NULL;
    PyObject *value = NULL;
    PyObject *traceback = NULL;
    PyObject *params = NULL;

    PyObject *error_message = NULL;
    PyObject *stack_trace = NULL;

    NRSettingsObject *settings = NULL;

    static char *kwlist[] = { "type", "value", "traceback", "params", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OOO!|O!:notice_error",
                                     kwlist, &type, &value, &PyTraceBack_Type,
                                     &traceback, &PyDict_Type, &params)) {
        return NULL;
    }

    if (self->transaction_state != NR_TRANSACTION_STATE_RUNNING) {
        PyErr_SetString(PyExc_RuntimeError, "transaction not active");
        return NULL;
    }

    /*
     * If the application was not enabled and so we are running
     * as a dummy transaction then return without actually doing
     * anything.
     */

    if (!self->transaction) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    /*
     * Only continue if the error collector is enabled and back
     * end server application says we should collect errors.
     */

    if (!nr_per_process_globals.errors_enabled) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    if (!self->application->application->collect_errors) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    /* Capture details if valid exception. */

    if (type != Py_None && value != Py_None) {
        PyObject *item = NULL;

        PyObject *name = NULL;

        settings = (NRSettingsObject *)NRSettings_Singleton();

        /*
         * Check whether this is an error type we should ignore.
         * Note that where the value is an instance type, the
         * name has to be obtained from the associated class
         * definition object.
         */

        if (PyInstance_Check(value)) {
            PyObject *module = NULL;
            PyObject *class = NULL;
            PyObject *object = NULL;

            class = PyObject_GetAttrString(value, "__class__");

            if (class) {
                module = PyObject_GetAttrString(class, "__module__");
                object = PyObject_GetAttrString(class, "__name__");

                if (module) {
                    name = PyString_FromFormat("%s.%s",
                                               PyString_AsString(module),
                                               PyString_AsString(object));
                }
                else {
                    Py_INCREF(object);
                    name = object;
                }
            }

            PyErr_Clear();

            Py_XDECREF(object);
            Py_XDECREF(class);
            Py_XDECREF(module);
        }

        if (name) {
            item = PyDict_GetItem(
                    settings->errors_settings->ignore_errors, name);
        }
        else {
            item = PyDict_GetItemString(
                    settings->errors_settings->ignore_errors,
                    Py_TYPE(value)->tp_name);
        }

        if (!item) {
#if 0
            PyObject *dict = NULL;
            PyObject *object = NULL;

            PyObject *module = NULL;
#endif

            error_message = NRUtilities_FormatObject(value);
            stack_trace = NRUtilities_FormatException(type, value, traceback);

            if (!stack_trace)
               PyErr_Clear();

            if (name) {
                record = nr_transaction_error__allocate(
                        self->transaction, &(self->transaction_errors),
                        "", 0, PyString_AsString(error_message),
                        PyString_AsString(name), 0);
            }
            else
            {
                record = nr_transaction_error__allocate(
                        self->transaction, &(self->transaction_errors),
                        "", 0, PyString_AsString(error_message),
                        Py_TYPE(value)->tp_name, 0);
            }

            if (stack_trace) {
                nro__set_hash_string(record->params, "stack_trace",
                                     PyString_AsString(stack_trace));
#if 0
                /*
                 * XXX How source code can be recorded when RPM UI
                 * actually displays it.
                 */
                nro__set_hash_string(record->params, "file_name", "FILENAME");
                nro__set_hash_string(record->params, "line_number", "LINENUMBER");
                nro__set_hash_string(record->params, "source", "SOURCE #1\nSOURCE #2");
#endif
            }

#if 0
            dict = PyDict_New();

            object = PySys_GetObject("path");
            PyDict_SetItemString(dict, "sys.path", object);

            module = PyImport_ImportModule("os");

            if (module) {
                PyObject *environ = NULL;

                environ = PyObject_GetAttrString(module, "environ");

                if (environ) {
                    object = PyDict_GetItemString(environ, "PYTHON_EGG_CACHE");
                    if (object)
                        PyDict_SetItemString(dict, "PYTHON_EGG_CACHE", object);
                    Py_DECREF(environ);
                }


                PyErr_Clear();

                Py_DECREF(module);
            }

            NRUtilities_MergeDictIntoParams(record->params,
                                            "custom_parameters", dict);

            Py_DECREF(dict);
#endif

            if (params) {
                NRUtilities_MergeDictIntoParams(record->params,
                                                "custom_parameters", params);
            }

            /*
             * TODO There is also provision for passing back
             * 'file_name', 'line_number' and 'source' params as
             * well. These are dependent on RPM have been updated
             * to show them for something other than Ruby. The
             * passing back of such additional information as the
             * source code should be done by setting a flag and
             * not be on by default. The file name and line number
             * may not display in RPM the source code isn't also
             * sent. Need to see how RPM is changed. See details in:
             * https://www.pivotaltracker.com/story/show/7922639
             */

            /*
             * TODO Are there any default things that could be added
             * to the custom parameters for this unhandled exception
             * case. What about stack variables and values associated
             * with them. These should only be passed back though
             * if enabled through a flag.
             */

            Py_XDECREF(stack_trace);
            Py_DECREF(error_message);
        }
        
        Py_XDECREF(name);
    }

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRTransaction_name_transaction(
        NRTransactionObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *bytes = NULL;

    PyObject *name = NULL;
    PyObject *scope = Py_None;

    static char *kwlist[] = { "name", "scope", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O|O:name_transaction",
                                     kwlist, &name, &scope)) {
        return NULL;
    }

    /*
     * Raise an exception if the path has been frozen and should
     * no longer be modified. The path would be frozen upon the
     * footer being generated for RUM as that encodes the path
     * into a magic key which is included in the footer. If the
     * path is changed after that, then will not be possible to
     * correlate data from RUM and agent. An exception is raised
     * to highlight that a problem exists in way instrumentation
     * is done. Specifically, that transaction should always be
     * named prior to generation of footer for RUM.
     */

    if (self->path_frozen) {
        PyErr_SetString(PyExc_TypeError, "transaction name has been "
                        "frozen and can no longer be updated");
        return NULL;
    }

    /*
     * If the application was not enabled and so we are running
     * as a dummy transaction then return without actually doing
     * anything.
     */

    if (!self->transaction) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    /*
     * XXX No ability in PHP agent core yet to override scope so
     * we just append to a custom prefix.
     */

    nrfree(self->transaction->path);

    bytes = NRUtilities_ConstructPath(name, scope);
    self->transaction->path_type = NR_PATH_TYPE_RAW;
    self->transaction->path = nrstrdup(PyString_AsString(bytes));
    Py_DECREF(bytes);

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRTransaction_get_application(NRTransactionObject *self,
                                               void *closure)
{
    Py_INCREF(self->application);
    return (PyObject *)self->application;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRTransaction_get_ignore(NRTransactionObject *self,
                                          void *closure)
{
    /*
     * If the application was not enabled and so we are running
     * as a dummy transaction then return that transaction is
     * being ignored.
     */

    if (!self->transaction) {
        Py_INCREF(Py_True);
        return Py_True;
    }

    return PyBool_FromLong(self->transaction->ignore);
}

/* ------------------------------------------------------------------------- */

static int NRTransaction_set_ignore(NRTransactionObject *self,
                                    PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "can't delete ignore attribute");
        return -1;
    }

    if (!PyBool_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected bool for ignore attribute");
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
        self->transaction->ignore = 1;
    else
        self->transaction->ignore = 0;

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRTransaction_get_ignore_apdex(NRTransactionObject *self,
                                                void *closure)
{
    /*
     * If the application was not enabled and so we are running
     * as a dummy transaction then return that transaction is
     * being ignored.
     */

    if (!self->transaction) {
        Py_INCREF(Py_True);
        return Py_True;
    }

    return PyBool_FromLong(self->transaction->ignore_apdex);
}

/* ------------------------------------------------------------------------- */

static int NRTransaction_set_ignore_apdex(NRTransactionObject *self,
                                          PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError,
                "can't delete ignore_apdex attribute");
        return -1;
    }

    if (!PyBool_Check(value)) {
        PyErr_SetString(PyExc_TypeError,
                "expected bool for ignore_apdex attribute");
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
        self->transaction->ignore_apdex = 1;
    else
        self->transaction->ignore_apdex = 0;

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRTransaction_get_path(NRTransactionObject *self,
                                        void *closure)
{
    /*
     * If the application was not enabled and so we are running
     * as a dummy transaction then return None.
     */

    if (!self->transaction) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    return PyString_FromString(self->transaction->path);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRTransaction_get_enabled(NRTransactionObject *self,
                                           void *closure)
{
    if (self->transaction) {
        Py_INCREF(Py_True);
        return Py_True;
    }

    Py_INCREF(Py_False);
    return Py_False;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRTransaction_get_coroutines(NRTransactionObject *self,
                                              void *closure)
{
    if (self->coroutines) {
        Py_INCREF(Py_True);
        return Py_True;
    }

    Py_INCREF(Py_False);
    return Py_False;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRTransaction_get_background_task(NRTransactionObject *self,
                                                   void *closure)
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

static PyObject *NRTransaction_get_custom_parameters(
        NRTransactionObject *self, void *closure)
{
    Py_INCREF(self->custom_parameters);

    return self->custom_parameters;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRTransaction_get_request_parameters(
        NRTransactionObject *self, void *closure)
{
    Py_INCREF(self->request_parameters);

    return self->request_parameters;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRTransaction_get_capture_params(NRTransactionObject *self,
                                                  void *closure)
{
    return PyBool_FromLong(self->capture_params);
}

/* ------------------------------------------------------------------------- */

static int NRTransaction_set_capture_params(NRTransactionObject *self,
                                            PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "can't delete capture_params attribute");
        return -1;
    }

    if (!PyBool_Check(value)) {
        PyErr_SetString(PyExc_TypeError,
                        "expected bool for capture_params attribute");
        return -1;
    }

    if (value == Py_True)
        self->capture_params = 1;
    else
        self->capture_params = 0;

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRTransaction_get_ignored_params(NRTransactionObject *self,
                                                  void *closure)
{
    Py_INCREF(self->ignored_params);
    return self->ignored_params;
}

/* ------------------------------------------------------------------------- */

static int NRTransaction_set_ignored_params(NRTransactionObject *self,
                                            PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "can't delete ignored_params attribute");
        return -1;
    }

    if (!PyList_Check(value)) {
        PyErr_SetString(PyExc_TypeError,
                        "expected list for ignored_params attribute");
        return -1;
    }

    Py_INCREF(value);
    Py_DECREF(self->ignored_params);
    self->ignored_params = value;

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRTransaction_get_response_code(
        NRTransactionObject *self, void *closure)
{
    /*
     * If the application was not enabled and so we are running
     * as a dummy transaction then return 0 as response code.
     */

    if (!self->transaction)
        return PyInt_FromLong(0);

    return PyInt_FromLong(self->transaction->http_response_code);
}

/* ------------------------------------------------------------------------- */

static int NRTransaction_set_response_code(
        NRTransactionObject *self, PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "can't delete response code attribute");
        return -1;
    }

    if (!PyInt_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected integer for response code");
        return -1;
    }

    /*
     * If the application was not enabled and so we are running
     * as a dummy transaction then return without actually doing
     * anything.
     */

    if (!self->transaction)
        return 0;

    self->transaction->http_response_code = PyInt_AsLong(value);

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyMethodDef NRTransaction_methods[] = {
    { "__enter__",          (PyCFunction)NRTransaction_enter,
                            METH_NOARGS, 0 },
    { "__exit__",           (PyCFunction)NRTransaction_exit,
                            METH_VARARGS, 0 },
    { "notice_error",       (PyCFunction)NRTransaction_notice_error,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "name_transaction",   (PyCFunction)NRTransaction_name_transaction,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { NULL, NULL }
};

static PyGetSetDef NRTransaction_getset[] = {
    { "application",        (getter)NRTransaction_get_application,
                            NULL, 0 },
    { "ignore",             (getter)NRTransaction_get_ignore,
                            (setter)NRTransaction_set_ignore, 0 },
    { "ignore_apdex",       (getter)NRTransaction_get_ignore_apdex,
                            (setter)NRTransaction_set_ignore_apdex, 0 },
    { "path",               (getter)NRTransaction_get_path,
                            NULL, 0 },
    { "enabled",            (getter)NRTransaction_get_enabled,
                            NULL, 0 },
    { "coroutines",         (getter)NRTransaction_get_coroutines,
                            NULL, 0 },
    { "background_task",    (getter)NRTransaction_get_background_task,
                            NULL, 0 },
    { "custom_parameters",  (getter)NRTransaction_get_custom_parameters,
                            NULL, 0 },
    { "request_parameters", (getter)NRTransaction_get_request_parameters,
                            NULL, 0 },
    { "capture_params",     (getter)NRTransaction_get_capture_params,
                            (setter)NRTransaction_set_capture_params, 0 },
    { "ignored_params",     (getter)NRTransaction_get_ignored_params,
                            (setter)NRTransaction_set_ignored_params, 0 },
    { "response_code",      (getter)NRTransaction_get_response_code,
                            (setter)NRTransaction_set_response_code, 0 },
    { NULL },
};

PyTypeObject NRTransaction_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.Transaction", /*tp_name*/
    sizeof(NRTransactionObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRTransaction_dealloc, /*tp_dealloc*/
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
    Py_TPFLAGS_DEFAULT |
    Py_TPFLAGS_BASETYPE,    /*tp_flags*/
    0,                      /*tp_doc*/
    0,                      /*tp_traverse*/
    0,                      /*tp_clear*/
    0,                      /*tp_richcompare*/
    0,                      /*tp_weaklistoffset*/
    0,                      /*tp_iter*/
    0,                      /*tp_iternext*/
    NRTransaction_methods,  /*tp_methods*/
    0,                      /*tp_members*/
    NRTransaction_getset,   /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)NRTransaction_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRTransaction_new,      /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

/*
 * vim: set cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
