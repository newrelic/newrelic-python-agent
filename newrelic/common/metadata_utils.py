

def get_function_filename_linenumber(function):
    filename = line_number = None
    try:
        if hasattr(function, "__code__"):
            co = function.__code__
        elif hasattr(function, "__func__"):
            co = function.__func__.__code__
        filename = co.co_filename
        line_number = co.co_firstlineno
    except:
        pass

    return filename, line_number
