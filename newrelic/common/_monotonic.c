/*
 * Copyright 2010 New Relic, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/*
 * This file is a modified back port of the monotonic() function from
 * Python 3.3. The original code was released under the Python Software
 * Foundation License Version 2.
 */

#include <Python.h>

#include <time.h>

#if defined(__APPLE__)
#include <mach/mach.h>
#include <mach/mach_time.h>
#endif

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

/* ------------------------------------------------------------------------- */

static PyObject *monotonic(PyObject *self, PyObject *args)
{
#if defined(MS_WINDOWS)
    static ULONGLONG (*GetTickCount64) (void) = NULL;
    static ULONGLONG (CALLBACK *Py_GetTickCount64)(void);
    static int has_getickcount64 = -1;
    double result;

    if (has_getickcount64 == -1) {
        /* GetTickCount64() was added to Windows Vista */
        if (winver.dwMajorVersion >= 6) {
            HINSTANCE hKernel32;
            hKernel32 = GetModuleHandleW(L"KERNEL32");
            *(FARPROC*)&Py_GetTickCount64 = GetProcAddress(hKernel32,
                                                           "GetTickCount64");
            has_getickcount64 = (Py_GetTickCount64 != NULL);
        }
        else
            has_getickcount64 = 0;
    }

    if (has_getickcount64) {
        ULONGLONG ticks;
        ticks = Py_GetTickCount64();
        result = (double)ticks * 1e-3;
    }
    else {
        static DWORD last_ticks = 0;
        static DWORD n_overflow = 0;
        DWORD ticks;

        ticks = GetTickCount();
        if (ticks < last_ticks)
            n_overflow++;
        last_ticks = ticks;

        result = ldexp(n_overflow, 32);
        result += ticks;
        result *= 1e-3;
    }

    return PyFloat_FromDouble(result);

#elif defined(__APPLE__)
    static mach_timebase_info_data_t timebase;
    uint64_t time;
    double secs;

    if (timebase.denom == 0) {
        /* According to the Technical Q&A QA1398, mach_timebase_info() cannot
           fail: https://developer.apple.com/library/mac/#qa/qa1398/ */
        (void)mach_timebase_info(&timebase);
    }

    time = mach_absolute_time();
    secs = (double)time * timebase.numer / timebase.denom * 1e-9;

    return PyFloat_FromDouble(secs);

#elif (defined(CLOCK_HIGHRES) || defined(CLOCK_MONOTONIC))
    struct timespec tp;
#ifdef CLOCK_HIGHRES
    const clockid_t clk_id = CLOCK_HIGHRES;
#else
    const clockid_t clk_id = CLOCK_MONOTONIC;
#endif

    if (clock_gettime(clk_id, &tp) != 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }

    return PyFloat_FromDouble(tp.tv_sec + tp.tv_nsec * 1e-9);
#else
    PyErr_SetNone(PyExc_NotImplementedError);
    return NULL;
#endif
}

/* ------------------------------------------------------------------------- */

static PyMethodDef monotonic_methods[] = {
    { "monotonic",          (PyCFunction)monotonic, METH_NOARGS, 0 },
    { NULL, NULL }
};

#if PY_MAJOR_VERSION >= 3
static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "_monotonic",        /* m_name */
    NULL,                /* m_doc */
    -1,                  /* m_size */
    monotonic_methods,   /* m_methods */
    NULL,                /* m_reload */
    NULL,                /* m_traverse */
    NULL,                /* m_clear */
    NULL,                /* m_free */
};
#endif

static PyObject *
moduleinit(void)
{
    PyObject *module;

#if PY_MAJOR_VERSION >= 3
    module = PyModule_Create(&moduledef);
#else
    module = Py_InitModule3("_monotonic", monotonic_methods, NULL);
#endif

    if (module == NULL)
        return NULL;

    return module;
}

#if PY_MAJOR_VERSION < 3
PyMODINIT_FUNC init_monotonic(void)
{
    moduleinit();
}
#else
PyMODINIT_FUNC PyInit__monotonic(void)
{
    return moduleinit();
}
#endif

/* ------------------------------------------------------------------------- */

