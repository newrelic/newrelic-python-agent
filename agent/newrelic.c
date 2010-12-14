/* ------------------------------------------------------------------------- */

#include "globals.h"

#include "application_data.h"
#include "generic_object_data.h"

/* ------------------------------------------------------------------------- */

ZEND_DECLARE_MODULE_GLOBALS(newrelic)

struct _nr_per_process_globals nr_per_process_globals;

void nr__put_stack_trace_into_params(nr_param_array* params) {
}

void nr_initialize_global_tt_threshold_from_apdex (nr_application* app) {
    if( nr_per_process_globals.tt_threshold_is_apdex_f ) {
        if( app != NULL ) {
            nr_per_process_globals.tt_threshold = app->apdex_t * 4;
        } else {
            nr_per_process_globals.tt_threshold = 500 * 1000 * 4;
        }
    }
}

/* ------------------------------------------------------------------------- */
