"""
sanitise any input that has unauthorised javascript/html tags in it

Let through only tags and attributes in the whitelists allowed_elements 
and allowed_attributes.

These can be specified in tiddlywebconfig.py.
"""
import html5lib
from html5lib.sanitizer import HTMLSanitizer
from html5lib.tokenizer import HTMLTokenizer
from html5lib.constants import tokenTypes
from html5lib.treebuilders import getTreeBuilder
import re
from xml.sax.saxutils import escape, unescape

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
    HTMLValidator.allowed_elements = config.get('allowed_elements', \
        HTMLValidator.allowed_elements)
    HTMLValidator.allowed_attributes = config.get('allowed_attributes', \
        HTMLValidator.allowed_attributes)

def sanitize_html_fragment(fragment, flag=False):
    """
    Sanitize an html fragment, returning a copy of the fragment,
    cleaned up. We use the newly defined Sanitizer
    """
    parser = html5lib.HTMLParser(tokenizer=HTMLValidator)
    output = parser.parseFragment(fragment, useChardet=False)
    
    response = output.toxml()
    return response