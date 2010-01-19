"""
sanitise any input that has unauthorised javascript/html tags in it

Let through only tags and attributes in the whitelists allowed_elements 
and allowed_attributes.

These can be specified in tiddlywebconfig.py.
"""
from tiddlyweb.web.validator import TIDDLER_VALIDATORS
from tiddlyweb.model.tiddler import Tiddler

import html5lib
from html5lib.sanitizer import HTMLSanitizer

class HTMLValidator(HTMLSanitizer):
    allowed_elements=['html', 'p', 'i', 'strong', 'b', 'u', 'a', 'h1',
        'h2', 'h3', 'h4', 'h5', 'h6', 'pre', 'br', 'img', 'span', 'em',
        'strike', 'sub', 'sup', 'address', 'font', 'table', 'tbody',
        'tr', 'td', 'ol', 'ul', 'li', 'div']
    
    allowed_attributes=['href', 'src', 'alt', 'title']
    

def update_whitelist(config):
    """
    read any specified whitelist from config, specifically:
    
    config={
        'allowed_elements': [],
        'allowed_attributes': []
    }
    default to ALLOWED_ELEMENTS and ALLOWED_ATTRIBUTES if none specified
    """
    if config.get('allowed_elements'):
        HTMLValidator.allowed_elements = config['allowed_elements']
    if config.get('allowed_attributes'):
        HTMLValidator.allowed_attributes = config['allowed_attributes']

def sanitize_html_fragment(fragment):
    """
    Sanitize an html fragment, returning a copy of the fragment,
    cleaned up. We use the newly defined Sanitizer
    """
    parser = html5lib.HTMLParser(tokenizer=HTMLValidator)
    output = parser.parseFragment(fragment)
    return output.toxml()

def sanitize(tiddler,environ):
    """
    pass all fields, tags, text and title into sanitize_html_fragment
    """
    print 'text: ', tiddler.text
    for field,value in tiddler.fields.iteritems():     
        tiddler.fields[field] = sanitize_html_fragment(value)
    print 'running text'
    tiddler.text = sanitize_html_fragment(tiddler.text)      
    tiddler.tags = map(sanitize_html_fragment,tiddler.tags)
    tiddler.title = sanitize_html_fragment(tiddler.title)
    print 'new text: ',tiddler.text

def init(config):
    """
    init function
    """
    update_whitelist(config)
    
    TIDDLER_VALIDATORS.append(sanitize)

