'''
Created on Jul 27, 2011

@author: sdaubin
'''

'''
This is where we'll implement the sql obfuscator, explain plan running, sql tracer, etc.
'''

import re

def obfuscator(database_type="postgresql"):
    if database_type == "mysql":
        return MysqlObfuscator()
    elif database_type == "postgresql":
        return PostgresqlObfuscator()

class SqlObfuscator:
    def numeric(self, sql):
        return re.sub(r'\d+', "?", sql)

    def single_quoted_string(self, sql):
        return re.sub(r"'(.*?[^\\'])??'(?!')", "?", sql)

    def double_quoted_string(self, sql):
        return re.sub(r'"(.*?[^\\"])??"(?!")', "?", sql)

class PostgresqlObfuscator(SqlObfuscator):
    def obfuscate(self, sql):
        return self.single_quoted_string(self.numeric(sql))

class MysqlObfuscator(SqlObfuscator):
    def obfuscate(self, sql):
        return self.double_quoted_string(self.single_quoted_string(self.numeric(sql)))
