"""
sanitize any input that has unauthorised javascript/html tags in it

Let through only tags and attributes in the whitelists allowed_elements 
and allowed_attributes.

These can be specified in tiddlywebconfig.py.
"""
from sanitizer import update_whitelist, sanitize_html_fragment

from tiddlyweb.web.validator import TIDDLER_VALIDATORS


def sanitize(tiddler,environ):
    """
    pass all fields, tags, text and title into sanitize_html_fragment
    """
    for field,value in tiddler.fields.iteritems():     
        tiddler.fields[field] = sanitize_html_fragment(value)
    tiddler.text = sanitize_html_fragment(tiddler.text)      
    tiddler.tags = map(sanitize_html_fragment,tiddler.tags)
    tiddler.title = sanitize_html_fragment(tiddler.title)

def init(config):
    """
    init function
    """
    update_whitelist(config)
    
    TIDDLER_VALIDATORS.append(sanitize)

