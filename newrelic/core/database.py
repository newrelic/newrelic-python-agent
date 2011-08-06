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
    numeric              = NormalizationRule(r'\d+', "?")
    single_quoted_string = NormalizationRule(r"'(.*?[^\\'])??'(?!')", "?")
    double_quoted_string = NormalizationRule(r'"(.*?[^\\"])??"(?!")', "?")

    if database_type == "mysql":
        return SqlObfuscator(numeric, single_quoted_string,
                             double_quoted_string)
    elif database_type == "postgresql":
        return SqlObfuscator(numeric, single_quoted_string)

class SqlObfuscator(Normalizer):
    def obfuscate(self, sql):
        return self.normalize(sql)
