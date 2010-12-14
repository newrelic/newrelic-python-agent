/* ------------------------------------------------------------------------- */

#include <Python.h>

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) \
        PyObject_HEAD_INIT(type) size,
#endif

#include "globals.h"
#include "logging.h"

#include "web_transaction_data.h"

#include "application_funcs.h"
#include "daemon_protocol_funcs.h"
#include "generic_object_funcs.h"
#include "harvest_funcs.h"
#include "metric_table_funcs.h"
#include "web_transaction_funcs.h"

#include "php_newrelic.h"

/* ------------------------------------------------------------------------- */

typedef struct {
    PyObject_HEAD
    nr_application *application;
    nr_web_transaction *web_transaction;
} NRWebTransactionObject;

static PyTypeObject NRWebTransaction_Type;

static NRWebTransactionObject *newNRWebTransactionObject(
        nr_application *application, const char *path, int path_type,
        int64_t start)
{
    NRWebTransactionObject *self;

    /*
     * Create transaction object and cache reference to the
     * internal agent client application object instance. Will
     * need the latter when doing some work arounds for lack
     * of thread safety in agent client code.
     */

    self = PyObject_New(NRWebTransactionObject, &NRWebTransaction_Type);
    if (self == NULL)
        return NULL;

    self->application = application;

    self->web_transaction = nr_web_transaction__allocate();
    self->web_transaction->path_type = path_type;
    self->web_transaction->path = nrstrdup(path);
    self->web_transaction->realpath = nrstrdup("/xxx");

    self->web_transaction->http_x_request_start = start;

    return self;
}

static void NRWebTransaction_dealloc(NRWebTransactionObject *self)
{
    /* XXX Don't think this is needed as harvest always reclaims it.
    nr_web_transaction__destroy(self->web_transaction);
    */
}

static PyObject *NRWebTransaction_enter(NRWebTransactionObject *self,
                                        PyObject *args)
{
    nr_node_header *save;

    nr_node_header__record_starttime_and_push_current(
            (nr_node_header *)self->web_transaction, &save);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *NRWebTransaction_exit(NRWebTransactionObject *self,
                                       PyObject *args)
{
    nr_node_header__record_stoptime_and_pop_current(
            (nr_node_header *)self->web_transaction, NULL);

    self->web_transaction->http_response_code = 200;

    pthread_mutex_lock(&(nr_per_process_globals.harvest_data_mutex));
    nr__switch_to_application(self->application);
    nr__distill_web_transaction_into_harvest_data(self->web_transaction);
    pthread_mutex_unlock(&(nr_per_process_globals.harvest_data_mutex));

    Py_INCREF(Py_None);
    return Py_None;
}

static PyMethodDef NRWebTransaction_methods[] = {
    { "__enter__",  (PyCFunction)NRWebTransaction_enter,  METH_NOARGS, 0 },
    { "__exit__",   (PyCFunction)NRWebTransaction_exit,   METH_VARARGS, 0 },
    { NULL, NULL }
};

static PyGetSetDef NRWebTransaction_getset[] = {
    { NULL },
};

static PyTypeObject NRWebTransaction_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.WebTransaction", /*tp_name*/
    sizeof(NRWebTransactionObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRWebTransaction_dealloc, /*tp_dealloc*/
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
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    0,                      /*tp_init*/
    0,                      /*tp_alloc*/
    0,                      /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

typedef struct {
    PyObject_HEAD
    nr_application *application;
} NRApplicationObject;

static PyTypeObject NRApplication_Type;

static int NRApplication_instances = 0;

static void NRApplication_populate_environment(void)
{
    PyObject *module = NULL;

    /*
     * Gather together Python configuration information that is
     * usually exposed in the 'sys' module. We don't include
     * 'sys.path' as that can be different for each sub
     * interpreter and can also change over the lifetime of the
     * process.
     */

    nr_generic_object__add_string_to_hash(nr_per_process_globals.env,
                                          "Python Program Name",
                                          Py_GetProgramName());
    nr_generic_object__add_string_to_hash(nr_per_process_globals.env,
                                          "Python Home", Py_GetPythonHome());

    nr_generic_object__add_string_to_hash(nr_per_process_globals.env,
                                          "Python Program Full Path",
                                          Py_GetProgramFullPath());
    nr_generic_object__add_string_to_hash(nr_per_process_globals.env,
                                          "Python Prefix", Py_GetPrefix());
    nr_generic_object__add_string_to_hash(nr_per_process_globals.env,
                                          "Python Exec Prefix",
                                          Py_GetPrefix());
    nr_generic_object__add_string_to_hash(nr_per_process_globals.env,
                                          "Python Version", Py_GetVersion());
    nr_generic_object__add_string_to_hash(nr_per_process_globals.env,
                                          "Python Platform", Py_GetPlatform());
    nr_generic_object__add_string_to_hash(nr_per_process_globals.env,
                                          "Python Copyright",
                                          Py_GetCopyright());
    nr_generic_object__add_string_to_hash(nr_per_process_globals.env,
                                          "Python Compiler",
                                          Py_GetCompiler());
    nr_generic_object__add_string_to_hash(nr_per_process_globals.env,
                                          "Python Build Info",
                                          Py_GetBuildInfo());
    
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
            PyObject *result = NULL;

            Py_INCREF(object);

            args = Py_BuildValue("(s)", "CONFIG_ARGS");
            result = PyEval_CallObject(object, args);

            if (result && result != Py_None) {
                nr_generic_object__add_string_to_hash(
                        nr_per_process_globals.env, "Python Config Args",
                        PyString_AsString(result));
            }
            else
                PyErr_Clear();

            Py_XDECREF(result);

            Py_DECREF(args);
            Py_DECREF(object);
        }
    }
    else
      PyErr_Clear();
}

static void NRApplication_populate_plugin_list(void)
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
    nr_generic_object* plugins;

    plugins = nr_generic_object__allocate(NR_OBJECT_ARRAY);
    plugins = nr_generic_object__add_object_to_hash(nr_per_process_globals.env,
                                                    "Plugin List", plugins);

    for (i = 0; PyImport_Inittab[i].name != NULL; i++) {
        if (!PyImport_Inittab[i].name)
            break;

        nr_generic_object__add_string_to_array(plugins,
                                               PyImport_Inittab[i].name) ;
    }
}

static void NRApplication_initialise(void)
{
    nr__log(LOG_DEBUG,"INITIALISE");

    nr__initialize_logging();

    pthread_mutex_init(&(nr_per_process_globals.daemon.lock),NULL);

    nr_per_process_globals.daemon.sockfd = -1;
    nr_per_process_globals.daemon.buffer = NULL;
    nr_per_process_globals.metric_limit = 2000;

    nr__initialize_overflow_metric();

    /* This will leak a file descriptor if do in process restart. */

    nr_per_process_globals.logfileptr = NULL;

    nr__initialize_applications_global();

#if 0
    nr_per_process_globals.orig_compile_file = zend_compile_file;
#endif

#if NR_HAVE_STACK_BACKTRACE
#if (0 - NR_THREADED)
    nr__log(LOG_INFO,"agent version %s (pthread,backtrace)",PHP_NEWRELIC_VERSION);
#else
    nr__log(LOG_INFO,"agent version %s (non-thread,backtrace)",PHP_NEWRELIC_VERSION);
#endif
#else
#if (0 - NR_THREADED)
    nr__log(LOG_INFO,"agent version %s (pthread)",PHP_NEWRELIC_VERSION);
#else
    nr__log(LOG_INFO,"agent version %s (non-thread)",PHP_NEWRELIC_VERSION);
#endif
#endif

    /* XXX */
#if 0
    nr_per_process_globals.enabled = 1;
#endif
    nr_per_process_globals.daemon.timeout = 1;
    nr_per_process_globals.daemon.nonblock = 0;
    nr_per_process_globals.loglevel = LOG_VERBOSEDEBUG;
    nr_per_process_globals.appname = "My Application";
    nr_per_process_globals.daemon.sockpath = "/tmp/.newrelic.sock";
    /* XXX */

    if( nr_per_process_globals.special_flags ) nr__log(LOG_INFO,"special.flags = 0x%x",nr_per_process_globals.special_flags);
    nr__log(LOG_DEBUG,"daemon socket is at %s (timeout=%d)",nr_per_process_globals.daemon.sockpath,nr_per_process_globals.daemon.timeout);
    nr__log(LOG_DEBUG,"MINIT");

    nr_per_process_globals.env = nr_generic_object__allocate(NR_OBJECT_HASH);

    NRApplication_populate_environment();
    NRApplication_populate_plugin_list();

    nr__create_harvest_thread();
}

static void NRApplication_shutdown(void)
{
    nr__log(LOG_DEBUG,"SHUTDOWN");
    
    nr__harvest_thread_body("shutdown");
    nr__stop_communication(&(nr_per_process_globals.daemon), NULL);
    nr__destroy_harvest_thread();

    nr__free_applications_global();

    /* XXX Currently a static string.
    nrfree(nr_per_process_globals.daemon.sockpath);
    */

    /* XXX This later should always be non NULL. */

    nr_generic_object__destroy(nr_per_process_globals.env);
}

static NRApplicationObject *newNRApplicationObject(const char *name)
{
    NRApplicationObject *self;

    /*
     * If this is the first instance, we need to (re)initialise
     * the agent client code. It may be a reinitialisation where
     * all application objects had been destroyed and so agent
     * client code had already been terminated and cleaned up.
     * We hold the Python GIL here so do not need to worry about
     * separate mutex locking when accessing global data.
     */

    if (!NRApplication_instances)
      NRApplication_initialise();

    NRApplication_instances++;

    /*
     * Create application object and cache reference to the
     * internal agent client application object instance. Will
     * need the latter when initiating a web transaction or
     * background task against this application instance.
     */

    self = PyObject_New(NRApplicationObject, &NRApplication_Type);
    if (self == NULL)
        return NULL;

    self->application = nr__find_or_create_application(name);

    return self;
}

static void NRApplication_dealloc(NRApplicationObject *self)
{
    /*
     * If this the last instance, we need to shutdown and
     * cleanup the agent client code. This includes flushing out
     * any data still to be sent to local daemon agent.
     * We hold the Python GIL here so do not need to worry about
     * separate mutex locking when accessing global data but do
     * release the GIL when performing shutdown of the agent
     * client code as it may want to talk over the network.
     */

    NRApplication_instances--;

    if (!NRApplication_instances) {
        Py_BEGIN_ALLOW_THREADS
        NRApplication_shutdown();
        Py_END_ALLOW_THREADS
    }
}

static PyObject *NRApplication_name(NRApplicationObject *self, void *closure)
{
    return PyString_FromString(self->application->appname);
}

static PyObject *NRApplication_web_transaction(NRApplicationObject *self, PyObject *args)
{
    NRWebTransactionObject *rv;

    rv = newNRWebTransactionObject(self->application, "/", NR_PATH_TYPE_URI, 0);
    if (rv == NULL)
        return NULL;

    return (PyObject *)rv;
}

static PyObject *NRApplication_new(PyObject *self, PyObject *args)
{
    NRApplicationObject *rv;
    const char *name;

    if (!PyArg_ParseTuple(args, "s:Application", &name))
        return NULL;

    rv = newNRApplicationObject(name);
    if (rv == NULL)
        return NULL;

    return (PyObject *)rv;
}


static PyMethodDef NRApplication_methods[] = {
    { "web_transaction",   (PyCFunction)NRApplication_web_transaction,   METH_VARARGS, 0 },
    { NULL, NULL}
};

static PyGetSetDef NRApplication_getset[] = {
    { "name", (getter)NRApplication_name, NULL, 0 },
    { NULL },
};

static PyTypeObject NRApplication_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.Application", /*tp_name*/
    sizeof(NRApplicationObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRApplication_dealloc, /*tp_dealloc*/
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
    NRApplication_methods,  /*tp_methods*/
    0,                      /*tp_members*/
    NRApplication_getset,   /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    0,                      /*tp_init*/
    0,                      /*tp_alloc*/
    0,                      /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyMethodDef newrelic_methods[] = {
    { "Application", NRApplication_new, METH_VARARGS, 0 },
    { NULL, NULL }
};

PyMODINIT_FUNC
init_newrelic(void)
{
    PyObject *m;

    m = Py_InitModule3("_newrelic", newrelic_methods, NULL);
    if (m == NULL)
        return;

    if (PyType_Ready(&NRApplication_Type) < 0)
        return;
    if (PyType_Ready(&NRWebTransaction_Type) < 0)
        return;
}

/* ------------------------------------------------------------------------- */
