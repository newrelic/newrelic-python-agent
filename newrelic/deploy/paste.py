import os

def filter_app_factory(app, global_conf, config_file, environment=None):
    os.environ['NEWRELIC_CONFIG_FILE'] = config_file
    if environment:
        os.environ['NEWRELIC_ENVIRONMENT'] = environment
    import newrelic.agent
    return newrelic.agent.WSGIApplicationWrapper(app)
