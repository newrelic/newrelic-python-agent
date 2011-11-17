import newrelic.api.external_trace

def instrument_pywapi(module):

    if hasattr(module, 'get_weather_from_weather_com'):
        newrelic.api.external_trace.wrap_external_trace(
               module, 'get_weather_from_weather_com', 'pywapi',
               module.WEATHER_COM_URL)

    if hasattr(module, 'get_weather_from_google'):
        newrelic.api.external_trace.wrap_external_trace(
               module, 'get_weather_from_google', 'pywapi',
               module.GOOGLE_WEATHER_URL)

    if hasattr(module, 'get_countries_from_google'):
        newrelic.api.external_trace.wrap_external_trace(
               module, 'get_countries_from_google', 'pywapi',
               module.GOOGLE_COUNTRIES_URL)

    if hasattr(module, 'get_cities_from_google'):
        newrelic.api.external_trace.wrap_external_trace(
               module, 'get_cities_from_google', 'pywapi',
               module.GOOGLE_CITIES_URL)

    if hasattr(module, 'get_weather_from_yahoo'):
        newrelic.api.external_trace.wrap_external_trace(
               module, 'get_weather_from_yahoo', 'pywapi',
               module.YAHOO_WEATHER_URL)

    if hasattr(module, 'get_weather_from_noaa'):
          newrelic.api.external_trace.wrap_external_trace(
                 module, 'get_weather_from_noaa', 'pywapi',
                 module.NOAA_WEATHER_URL)
