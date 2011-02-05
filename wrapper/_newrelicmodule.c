/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include <Python.h>

#include "py_settings.h"

#include "py_application.h"

#include "py_background_task.h"
#if 0
#include "py_database_trace.h"
#include "py_external_trace.h"
#include "py_function_trace.h"
#include "py_memcache_trace.h"
#endif
#include "py_transaction.h"
#include "py_web_transaction.h"

#include "globals.h"
#include "logging.h"

#include "application.h"
#include "daemon_protocol.h"
#include "genericobject.h"
#include "harvest.h"
#include "metric_table.h"
#include "web_transaction.h"

/* ------------------------------------------------------------------------- */

struct _nr_per_process_globals nr_per_process_globals;

#if 0
void nr_initialize_global_tt_threshold_from_apdex (nrapp_t *app) {
    if( nr_per_process_globals.tt_threshold_is_apdex_f ) {
        if( app != NULL ) {
            nr_per_process_globals.tt_threshold = app->apdex_t * 4;
        } else {
            nr_per_process_globals.tt_threshold = 500 * 1000 * 4;
        }
    }
}
#endif

/* ------------------------------------------------------------------------- */

static void newrelic_populate_environment(void)
{
    PyObject *module = NULL;

    /*
     * Gather together Python configuration information that is
     * usually exposed in the 'sys' module. We don't include
     * 'sys.path' as that can be different for each sub
     * interpreter and can also change over the lifetime of the
     * process.
     */

    nro__set_hash_string(nr_per_process_globals.env,
                         "Python Program Name", Py_GetProgramName());
    nro__set_hash_string(nr_per_process_globals.env,
                         "Python Home", Py_GetPythonHome());

    nro__set_hash_string(nr_per_process_globals.env,
                         "Python Program Full Path", Py_GetProgramFullPath());
    nro__set_hash_string(nr_per_process_globals.env,
                         "Python Prefix", Py_GetPrefix());
    nro__set_hash_string(nr_per_process_globals.env,
                         "Python Exec Prefix", Py_GetPrefix());
    nro__set_hash_string(nr_per_process_globals.env,
                         "Python Version", Py_GetVersion());
    nro__set_hash_string(nr_per_process_globals.env,
                         "Python Platform", Py_GetPlatform());
    nro__set_hash_string(nr_per_process_globals.env,
                         "Python Compiler", Py_GetCompiler());
    nro__set_hash_string(nr_per_process_globals.env,
                         "Python Build Info", Py_GetBuildInfo());
    
    /*
     * Also try and obtain the options supplied to the
     * 'configure' script when Python was built. It may not be
     * possible to get hold of this if the 'dev' variant of
     * Python package isn't installed as it relies on using
     * 'distutils' to extract the value of the 'CONFIG_ARGS'
     * variable from the 'Makefile' installed as part of the
     * 'dev' package for Python. If full installation of Python
     * has be done from source code, should be available. Is
     * only an issue when binary packages installed from a
     * repository are being used.
     */

    module = PyImport_ImportModule("distutils.sysconfig");

    if (module) {
        PyObject *dict = NULL;
        PyObject *object = NULL;

        dict = PyModule_GetDict(module);
        object = PyDict_GetItemString(dict, "get_config_var");

        if (object) {
            PyObject *args = NULL;
            PyObject *arg0 = NULL;
            PyObject *result = NULL;

            Py_INCREF(object);

            arg0 = PyString_FromString("CONFIG_ARGS");
            args = PyTuple_Pack(1, arg0);

            result = PyObject_Call(object, args, NULL);

            if (result && result != Py_None) {
                nro__set_hash_string(nr_per_process_globals.env,
                                     "Python Config Args",
                                     PyString_AsString(result));
            }
            else
                PyErr_Clear();

            Py_XDECREF(result);

            Py_DECREF(arg0);
            Py_DECREF(args);
            Py_DECREF(object);
        }
    }
    else
      PyErr_Clear();
}

static void newrelic_populate_plugin_list(void)
{
    /*
     * Closest we can get to a list of plugins in the list of
     * builtin modules. We can't use what is in sys.modules as
     * that will be different per sub interpreter and can change
     * over time due to dynamic loading of modules. Only gather
     * list of modules in 'sys.modules' when have an error we are
     * reporting.
     */

    int i;
    nrobj_t plugins;

    plugins = nro__new(NR_OBJECT_ARRAY);
    nro__set_hash_array(nr_per_process_globals.env, "Plugin List", plugins);

    for (i = 0; PyImport_Inittab[i].name != NULL; i++) {
        if (!PyImport_Inittab[i].name)
            break;

        nro__set_array_string (plugins, 0, PyImport_Inittab[i].name);
    }
}

static PyObject *newrelic_application(PyObject *self, PyObject *args,
                                      PyObject *kwds)
{
    return NRApplication_Singleton(args, kwds);
}

static PyObject *newrelic_settings(PyObject *self, PyObject *args)
{
    NRSettingsObject *rv;

    rv = NRSettings_New();
    if (rv == NULL)
        return NULL;

    return (PyObject *)rv;
}

static PyObject *newrelic_log(PyObject *self, PyObject *args, PyObject *kwds)
{
    int level = 0;
    const char *message = NULL;

    static char *kwlist[] = { "level", "message", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "is:log",
                                     kwlist, &level, &message)) {
        return NULL;
    }

    Py_BEGIN_ALLOW_THREADS
    nr__log(level, "%s", message);
    Py_END_ALLOW_THREADS

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *newrelic_harvest(PyObject *self, PyObject *args,
                                  PyObject *kwds)
{
    const char *reason = NULL;

    static char *kwlist[] = { "reason", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|z:harvest",
                                     kwlist, &reason)) {
        return NULL;
    }

    if (!reason)
        reason = "flush";

    Py_BEGIN_ALLOW_THREADS
    nr__harvest_thread_body(reason);
    Py_END_ALLOW_THREADS

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *newrelic_transaction(PyObject *self, PyObject *args)
{
    PyObject *result;

    result = NRTransaction_CurrentTransaction();

    if (result) {
        Py_INCREF(result);
        return result;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *newrelic_shutdown(PyObject *self, PyObject *args)
{
    static int shutdown = 0;

    if (!shutdown) {
        shutdown = 1;

        Py_BEGIN_ALLOW_THREADS

        nr__harvest_thread_body("shutdown");
        nr__stop_communication(&(nr_per_process_globals.daemon), NULL);
        nr__destroy_harvest_thread();

        nr__free_applications_global();
        nrfree (nr_per_process_globals.daemon.sockpath);
        if (nr_per_process_globals.env != NULL) {
            nro__delete (nr_per_process_globals.env);
        }

        Py_END_ALLOW_THREADS
    }

    Py_INCREF(Py_None);
    return Py_None;
}

#if 0
static PyMethodDef *newrelic_lookup_function(const char *mname,
                                             const char *cname,
                                             const char *fname)
{
    PyObject *module = NULL;

    PyMethodDef *function = NULL;

    module = PyImport_ImportModule(mname);

    if (module) {
        PyObject *dict = NULL;
        PyObject *cobject = NULL;
        PyObject *fobject = NULL;

        dict = PyModule_GetDict(module);

        if (cname) {
            PyTypeObject *tobject;
            PyMethodDef *methods;

            cobject = PyDict_GetItemString(dict, cname);

            if (!cobject || !PyType_Check(cobject)) {
                PyErr_SetString(PyExc_RuntimeError, "not a valid class type");
                Py_XDECREF(cobject);
                Py_DECREF(module);
                return NULL;
            }

            tobject = (PyTypeObject *)cobject;
            methods = tobject->tp_methods;
            while (methods->ml_name) {
                if (!strcmp(methods->ml_name, fname)) {
                    function = methods;
                    break;
                }
                methods++;
            }

            if (!function) {
                PyErr_SetString(PyExc_RuntimeError, "not a valid method");
                Py_DECREF(cobject);
                Py_XDECREF(fobject);
                Py_DECREF(module);
                return NULL;
            }

            Py_DECREF(cobject);
        }
        else {
            PyCFunctionObject *cfobject;

            fobject = PyDict_GetItemString(dict, fname);

            if (!fobject || !PyCFunction_Check(fobject)) {
                PyErr_SetString(PyExc_RuntimeError, "not a valid function");
                Py_XDECREF(fobject);
                Py_DECREF(module);
                return NULL;
            }

            cfobject = (PyCFunctionObject *)fobject;
            function = cfobject->m_ml;

            Py_DECREF(fobject);
        }

        Py_XDECREF(cobject);
    }
    else {
        PyErr_SetString(PyExc_RuntimeError, "not a valid module");
        return NULL;
    }

    Py_XDECREF(module);

    return function;
}

typedef struct {
    PyCFunction outer;
    const char *mname;
    const char *cname;
    const char *fname;
    int argnum;
    PyCFunction original;
    PyMethodDef *inner;
} NRMethodWrapper;

static NRMethodWrapper MRMethodWrapper_table[];

static PyObject *newrelic_call_database_trace(PyCFunction function, int argnum,
                                              PyObject *self, PyObject *args)
{
    PyObject *result = NULL;

    NRWebTransactionObject *object = NULL;

    nr_transaction_node *transaction_trace = NULL;
    nr_node_header *save = NULL;

    const char *sql = NULL;

    if (PyTuple_Check(args) && argnum > 0 && PyTuple_Size(args) >= argnum) {
        PyObject *object;

        object = PyTuple_GetItem(args, argnum-1);
        if (PyString_Check(object)) {
            sql = PyString_AsString(object);
        }
    }

    if (sql)
        object = NRWebTransaction_CurrentTransaction();

    if (object) {
        transaction_trace = nr_web_transaction__allocate_sql_node(
                object->web_transaction, sql, strlen(sql));

        nr_node_header__record_starttime_and_push_current(
                (nr_node_header *)transaction_trace, &save);
    }

    result = function(self, args);

    if (object) {
        nr_node_header__record_stoptime_and_pop_current(
                (nr_node_header *)transaction_trace, &save);

        /* TODO Only do this if slow. */

        /*
         * Treat any exception passed in as being unhandled and record
         * details of exception against the transaction.
         */

        PyObject *module;
        PyObject *result = NULL;

        module = PyImport_ImportModule("traceback");

        if (module) {
            PyObject *dict = NULL;
            PyObject *object = NULL;

            dict = PyModule_GetDict(module);
            object = PyDict_GetItemString(dict, "format_stack");

            if (object) {
                PyObject *args = NULL;

                Py_INCREF(object);

                args = PyTuple_New(0);
                result = PyObject_Call(object, args, NULL);

                Py_DECREF(args);
                Py_DECREF(object);

                if (!result) {
                    /* TODO Should be remembering old error and
                     * restoring it. */

                    PyErr_Clear();
                }
            }
        }
        else {
            /* TODO Should be remembering old error and
             * restoring it. */

            PyErr_Clear();
        }

        Py_XDECREF(module);

        if (result) {
            int i;

            transaction_trace->stacktrace_params = nr_param_array__allocate();

            for (i=0; i<PyList_Size(result); i++)
                nr_param_array__add_string_to_array_at(transaction_trace->stacktrace_params,"stack_trace", PyString_AsString(PyList_GetItem(result, i)));

        }

        Py_XDECREF(result);
    }

    return result;
}

static PyObject *newrelic_database_trace_0(PyObject *self, PyObject* args)
{
    NRMethodWrapper *wrapper;
    wrapper = &MRMethodWrapper_table[0];

    return newrelic_call_database_trace(wrapper->original, wrapper->argnum,
            self, args);
}

static PyObject *newrelic_database_trace_1(PyObject *self, PyObject* args)
{
    NRMethodWrapper *wrapper;
    wrapper = &MRMethodWrapper_table[1];

    return newrelic_call_database_trace(wrapper->original, wrapper->argnum,
            self, args);
}

static int NRMethodWrapper_count = 0;
static int NRMethodWrapper_maximum = 2;

static NRMethodWrapper MRMethodWrapper_table[] = {
    { newrelic_database_trace_0 },
    { newrelic_database_trace_1 },
};

static PyObject *newrelic_wrap_c_database_trace(PyObject *self, PyObject* args)
{
    const char *mname = NULL;
    const char *cname = NULL;
    const char *fname = NULL;
    int argnum;

    PyMethodDef *function;

    if (!PyArg_ParseTuple(args, "szsi", &mname, &cname, &fname, &argnum))
        return NULL;

    if (NRMethodWrapper_count >= NRMethodWrapper_maximum) {
        PyErr_SetString(PyExc_RuntimeError, "no more wrapper slots");
        return NULL;
    }

    function = newrelic_lookup_function(mname, cname, fname);

    if (!function)
        return NULL;

    MRMethodWrapper_table[NRMethodWrapper_count].mname = mname;
    MRMethodWrapper_table[NRMethodWrapper_count].cname = cname;
    MRMethodWrapper_table[NRMethodWrapper_count].fname = fname;

    MRMethodWrapper_table[NRMethodWrapper_count].argnum = argnum;

    MRMethodWrapper_table[NRMethodWrapper_count].original = function->ml_meth;

    MRMethodWrapper_table[NRMethodWrapper_count].inner = function;

    function->ml_meth = MRMethodWrapper_table[NRMethodWrapper_count].outer;

    NRMethodWrapper_count++;

    Py_INCREF(Py_None);
    return Py_None;
}
#endif

static PyMethodDef newrelic_methods[] = {
    { "application",        (PyCFunction)newrelic_application,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "settings",           newrelic_settings,
                            METH_NOARGS, 0 },
    { "log",                (PyCFunction)newrelic_log,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "harvest",            (PyCFunction)newrelic_harvest,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "transaction",        newrelic_transaction,
                            METH_NOARGS, 0 },
#if 0
    { "wrap_c_database_trace", newrelic_wrap_c_database_trace, METH_VARARGS, 0 },
#endif
    { NULL, NULL }
};

static PyMethodDef newrelic_method_shutdown = {
    "shutdown", newrelic_shutdown, METH_NOARGS, 0
};

PyMODINIT_FUNC
init_newrelic(void)
{
    PyObject *module;
    PyObject *atexit_module;

    PyGILState_STATE gil_state;

    pthread_mutexattr_t mutex_attr;

    module = Py_InitModule3("_newrelic", newrelic_methods, NULL);
    if (module == NULL)
        return;

    /* Initialise type objects. */

    if (PyType_Ready(&NRApplication_Type) < 0)
        return;
    if (PyType_Ready(&NRBackgroundTask_Type) < 0)
        return;
#if 0
    if (PyType_Ready(&NRDatabaseTrace_Type) < 0)
        return;
    if (PyType_Ready(&NRExternalTrace_Type) < 0)
        return;
    if (PyType_Ready(&NRFunctionTrace_Type) < 0)
        return;
    if (PyType_Ready(&NRMemcacheTrace_Type) < 0)
        return;
#endif
    if (PyType_Ready(&NRSettings_Type) < 0)
        return;
    if (PyType_Ready(&NRTransaction_Type) < 0)
        return;
    if (PyType_Ready(&NRWebTransaction_Type) < 0)
        return;

    /* Initialise type objects. */

    Py_INCREF(&NRBackgroundTask_Type);
    PyModule_AddObject(module, "BackgroundTask",
                       (PyObject *)&NRBackgroundTask_Type);

    Py_INCREF(&NRWebTransaction_Type);
    PyModule_AddObject(module, "WebTransaction",
                       (PyObject *)&NRWebTransaction_Type);

    /* Initialise module constants. */

    PyModule_AddObject(module, "LOG_ERROR",
                       PyInt_FromLong(LOG_ERROR));
    PyModule_AddObject(module, "LOG_INFO",
                       PyInt_FromLong(LOG_INFO));
    PyModule_AddObject(module, "LOG_WARNING",
                       PyInt_FromLong(LOG_WARNING));
    PyModule_AddObject(module, "LOG_VERBOSE",
                       PyInt_FromLong(LOG_VERBOSE));
    PyModule_AddObject(module, "LOG_DEBUG",
                       PyInt_FromLong(LOG_DEBUG));
    PyModule_AddObject(module, "LOG_VERBOSEDEBUG",
                       PyInt_FromLong(LOG_VERBOSEDEBUG));

    /*
     * TODO Don't install signal handlers for catching back
     * trace when crash at this time as can't test it on
     * MacOS X as is Linux specific. Could be added at some
     * point but then would clash if something like mod_wsgi
     * did the same thing. Really should be left up to the
     * hosting environment to do it and not this module.
     */

    /*
     * Initialise the daemon client mutex lock. This prevents
     * the harvest thread and daemon client code working on
     * accumulated data at the same time. Note that we always
     * rely on the ability to have a background thread for
     * performing harvesting. We do not support harvesting
     * being triggered as a side effect of request based on
     * a time since last harvest was performed. A recursive
     * mutex must be used because code which deals with the
     * daemon connection performs nested calls which attempt
     * to reacquire the thread mutex.
     */

    pthread_mutexattr_init(&mutex_attr);
    pthread_mutexattr_settype(&mutex_attr, PTHREAD_MUTEX_RECURSIVE);
    pthread_mutex_init(&(nr_per_process_globals.daemon.lock), &mutex_attr);
    pthread_mutexattr_destroy(&mutex_attr);

    /*
     * Logging initialisation in daemon client code is PHP
     * specific so set reasonable defaults here instead.
     * Initially there will be no log file and set level to be
     * INFO. Because the first time something is logged the log
     * file will be created, need to avoid doing any logging
     * during initialisation of this module. This provides
     * opportunity for user to override the log file location
     * and level immediately after they import this module.
     */

    nr_per_process_globals.logfilename = NULL;
    nr_per_process_globals.loglevel = LOG_INFO;
    nr_per_process_globals.logfileptr = NULL;

    /*
     * Initialise the daemon client socket information for the
     * connection to the local daemon process via the UNIX
     * socket. For values where it is sensible, these will be
     * able to be overridden via the settings object. Such
     * changes will be picked up next time need to connect to
     * the local daemon as part of the harvest cycle.
     */

    nr_per_process_globals.daemon.sockpath = nrstrdup("/tmp/.newrelic.sock");
    nr_per_process_globals.daemon.sockfd = -1;
    nr_per_process_globals.daemon.timeout = 10;
    nr_per_process_globals.daemon.nonblock = 1;
    nr_per_process_globals.daemon.buffer = NULL;

    /*
     * Initialise metrics table. The limit of number of metrics
     * collected per harvest file can be overriden via the
     * settings object and will apply next time harvest cycle
     * runs. Is a risk of it being changed mid cycle and so
     * limit different for different metrics tables, but not a
     * but issue.
     */

    nr_per_process_globals.metric_limit = 2000;

    nr__initialize_overflow_metric();

    /*
     * Initialise transaction tracing defaults. Transaction
     * tracing is on by default and can be overridden via the
     * settings object at any time and will apply on the
     * next harvest cycle.
     */

    nr_per_process_globals.tt_enabled = 1;
    nr_per_process_globals.tt_recordsql = 1;

    /* Initialise support for tracking multiple applications. */

    nr__initialize_applications_global();

    /* Initialise the global application environment. */

    nr_per_process_globals.env = nro__new(NR_OBJECT_HASH);

    newrelic_populate_environment();
    newrelic_populate_plugin_list();

    /*
     * Register shutdown method with atexit module for execution
     * on process shutdown. Because functions registered with
     * the atexit module are technically only invoked for the
     * main interpreter and not sub interpreters (except under
     * mod_wsgi), then we explicitly release the GIL and then
     * reacquire it against the main interpreter before actually
     * performing the registration. Note that under mod_python,
     * functions registered with the atexit module aren't called
     * at all as it doesn't properly shutdown the interpreter
     * when the process is being stopped. Since mod_python is
     * officially dead, use of it should be discouraged. Also be
     * aware that if both mod_python and mod_wsgi are loaded at
     * the same time into Apache, even if mod_python is not
     * actually used, mod_python controls interpreter
     * initialisation and destruction and so simply loading
     * mod_python causes any functions registered with atexit
     * module under mod_wsgi to not be called either.
     */

    Py_BEGIN_ALLOW_THREADS

    gil_state = PyGILState_Ensure();

    atexit_module = PyImport_ImportModule("atexit");

    if (atexit_module) {
        PyObject *module_dict = NULL;
        PyObject *register_function = NULL;

        module_dict = PyModule_GetDict(atexit_module);
        register_function = PyDict_GetItemString(module_dict, "register");

        if (register_function) {
            PyObject *callback_function = NULL;
            PyObject *args = NULL;
            PyObject *result = NULL;

            Py_INCREF(register_function);

            callback_function = PyCFunction_New(&newrelic_method_shutdown,
                                                NULL);

            args = PyTuple_Pack(1, callback_function);
            result = PyObject_Call(register_function, args, NULL);

            Py_DECREF(callback_function);
            Py_DECREF(args);
            Py_DECREF(register_function);

            Py_XDECREF(result);
        }

        Py_DECREF(atexit_module);
    }

    PyGILState_Release(gil_state);

    Py_END_ALLOW_THREADS
}

/* ------------------------------------------------------------------------- */

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
