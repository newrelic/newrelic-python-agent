#ifndef PY_AGENT_FIXUPS_H
#define PY_AGENT_FIXUPS_H

#define HAVE_CONFIG_H

#define ZTS

#define INTERNAL_FUNCTION_PARAMETERS void
#define ZEND_ATTRIBUTE_PTR_FORMAT(x, y, z)

#define TSRMLS_D void

#define TSRMLS_DC
#define TSRMLS_CC

#define TSRMG(x, y, z) (newrelic_globals.z)

#define zval int

#define zend_op_array int
#define zend_file_handle int
#define zend_op_array int
#define zend_bool int
#define zend_module_entry int

#define E_ERROR                         (1<<0L)
#define E_WARNING                       (1<<1L)
#define E_PARSE                         (1<<2L)
#define E_NOTICE                        (1<<3L)
#define E_CORE_ERROR            (1<<4L)
#define E_CORE_WARNING          (1<<5L)
#define E_COMPILE_ERROR         (1<<6L)
#define E_COMPILE_WARNING       (1<<7L)
#define E_USER_ERROR            (1<<8L)
#define E_USER_WARNING          (1<<9L)
#define E_USER_NOTICE           (1<<10L)
#define E_STRICT                        (1<<11L)
#define E_RECOVERABLE_ERROR     (1<<12L)
#define E_DEPRECATED            (1<<13L)
#define E_USER_DEPRECATED       (1<<14L)

#define E_ALL (E_ERROR | E_WARNING | E_PARSE | E_NOTICE | E_CORE_ERROR | E_CORE_WARNING | E_COMPILE_ERROR | E_COMPILE_WARNING | E_USER_ERROR | E_USER_WARNING | E_USER_NOTICE | E_RECOVERABLE_ERROR | E_DEPRECATED | E_USER_DEPRECATED)
#define E_CORE (E_CORE_ERROR | E_CORE_WARNING)

#define ZEND_BEGIN_MODULE_GLOBALS(module_name)          \
          typedef struct _zend_##module_name##_globals {
#define ZEND_END_MODULE_GLOBALS(module_name)            \
                    } zend_##module_name##_globals;

#define ZEND_DECLARE_MODULE_GLOBALS(module_name)                                                        \
          zend_##module_name##_globals module_name##_globals;
#define ZEND_EXTERN_MODULE_GLOBALS(module_name)                                                         \
          extern zend_##module_name##_globals module_name##_globals;

#define INI_STR(x) x
#define EG(x) 1

#define PHP_FUNCTION(x)

#define PHP_MINIT_FUNCTION(x)
#define PHP_MSHUTDOWN_FUNCTION(x)
#define PHP_RINIT_FUNCTION(x)
#define PHP_RSHUTDOWN_FUNCTION(x)
#define PHP_MINFO_FUNCTION(x)

#endif
