"""
TiddlyWebPages

by Ben Gillies
"""

from tiddlyweb.web.handler.recipe import get_tiddlers
from tiddlyweb.filters import parse_for_filters, recursive_filter
import re

def get_template(environ, start_response):
    """
    selector comes to this function when a custom url is found. 
    
    retrieve the recipe/serialization details and pass to 
    tiddlyweb.web.handler.recipe.get_tiddlers
    """
    #set url and extract variables
    url = environ['selector.matches'][0]
    patterned = len(environ['wsgiorg.routing_args'][1]) > 0 #are there variables to extract?
    if patterned:
        environ['recipe_extensions'] = {} 
        for element in environ['wsgiorg.routing_args'][1]:
            environ['recipe_extensions'][element] = environ['wsgiorg.routing_args'][1][element]

    #match the url with the appropriate entry in tw_pages_urls
    selector = environ['tiddlyweb.config']['selector']
    found = False
    for url_match in environ['tiddlyweb.config']['tw_pages_urls']:
        url_content = environ['tiddlyweb.config']['tw_pages_urls'][url_match]
        #check tiddler.text with selector to find out if it matches the url
        url_regex = selector.parser.__call__(url_match)
        if re.search(url_regex, url):
            url = url_match
            found = True
        if found:
            plugin_name = url_content['template']
            break
            
    #get any custom set filters and combine with any filters passed in via the query string
    if 'filter' in environ['tiddlyweb.config']['tw_pages_urls'][url]:
        filters = parse_for_filters(environ['tiddlyweb.config']['tw_pages_urls'][url]['filter'])[0]
        #strip duplicate filters
        filters = [custom_filter for custom_filter in filters if custom_filter.__name__ not in [environ_filter.__name__ for environ_filter in environ['tiddlyweb.filters']]]
        if len(environ['tiddlyweb.filters']) > 0:
            filters.extend(environ['tiddlyweb.filters'])
            
    #set up variables to pass into get_tiddlers
    environ['tiddlyweb.extension'] = str(plugin_name)
    environ['wsgiorg.routing_args'][1]['recipe_name'] = str(environ['tiddlyweb.config']['tw_pages_urls'][url]['recipe'])
    environ['tiddlyweb.filters'] = filters
    
    #set tiddlyweb.type to make sure we call the correct serializer
    try:
        mime_type = environ['tiddlyweb.config']['extension_types'][plugin_name]
    except KeyError:
        mime_type = 'default'
    environ['tiddlyweb.type'] = [mime_type]
    
    #set the title
    environ['tw_pages_title'] = environ['tiddlyweb.config']['tw_pages_urls'][url].get('title')
    
    return get_tiddlers(environ, start_response)