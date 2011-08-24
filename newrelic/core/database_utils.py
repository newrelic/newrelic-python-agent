'''
Created on Jul 27, 2011

@author: sdaubin
'''

'''
This is where we'll implement the sql obfuscator, explain plan running, sql tracer, etc.
'''

import re
from newrelic.core.string_normalization import *

def obfuscator(database_type="postgresql"):
    numeric              = DefaultNormalizationRule._replace(match=r'\d+', replacement="?")
    single_quoted_string = DefaultNormalizationRule._replace(match=r"'(.*?[^\\'])??'(?!')", replacement="?")
    double_quoted_string = DefaultNormalizationRule._replace(match=r'"(.*?[^\\"])??"(?!")', replacement="?")

    if database_type == "mysql":
        return SqlObfuscator(numeric, single_quoted_string,
                             double_quoted_string)
    elif database_type == "postgresql":
        return SqlObfuscator(numeric, single_quoted_string)

class SqlObfuscator(Normalizer):
    def obfuscate(self, sql):
        return self.normalize(sql)




def obfuscate_sql(module, sql):
    # FIXME Need to implement a mapping table for module.__name__ to
    # the appropriate obfuscator. Note that module can be None, in which
    # case maybe we should try and automatically attempt to derive
    # the type somehow instead. For now use postgresql.

    return obfuscator().obfuscate(sql)
