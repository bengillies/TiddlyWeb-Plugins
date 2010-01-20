"""
sanitize any input that has unauthorised javascript/html tags in it

Let through only tags and attributes in the whitelists allowed_tags
and allowed_attributes. These can be specified manually in
tiddlywebconfig.py.
"""
from tiddlyweb.web.validator import TIDDLER_VALIDATORS, InvalidTiddlerError

from tiddlyweb.manage import merge_config

from BeautifulSoup import BeautifulSoup, Comment
import re

VALIDATOR_CONFIG = {
    'allowed_tags': ['html', 'p', 'i', 'strong', 'b', 'u', 'a', 'h1', 'h2',
        'h3', 'h4', 'h5', 'h6', 'pre', 'br', 'img', 'span', 'em', 'strike',
        'sub', 'sup', 'address', 'font', 'table', 'tbody', 'tr', 'td', 'ol',
        'ul', 'li', 'div'],
    'allowed_attributes': ['href', 'src', 'alt', 'title']
}

def check_html(value, environ):
    """
    This function does the actual validation.
    environ must have 'allowed_tags' and
    'allowed_attributes' in it.
    
    Removes unwanted tags, attributes and
    comments.
    
    Value should be the string to be validated.
    """
    if type(value) != unicode:
        try:
            value = unicode(value)
        except UnicodeDecodeError:
            raise InvalidTiddlerError('HTML Validation Failed: contents of tiddler not a valid string.')
    
    url_regex = re.compile(r'[\s]*(&#x.{1,7})?'.join(list('javascript:'))) 
    
    soup = BeautifulSoup(value)
    
    for comment in soup.findAll(text=lambda text: isinstance(text, Comment)): 
        comment.extract()                                        
    
    for tag in soup.findAll(True):
        if tag.name not in environ['tiddlyweb.config']['allowed_tags']:
            tag.hidden = True
        tag.attrs = [(attr, url_regex.sub('', val)) for attr, val in tag.attrs
            if attr in environ['tiddlyweb.config']['allowed_attributes']]
                     
    return soup.renderContents().decode('utf8')


def validate(tiddler, environ):
    """
    Entry point for validator. Strip any unwanted
    tags or attributes.
    
    Check all fields, title, tags and text.
    """
    for field, value in tiddler.fields.iteritems():     
        tiddler.fields[field] = check_html(value, environ)
    tiddler.text = check_html(tiddler.text, environ)
    tiddler.tags = [check_html(tag, environ) for tag in tiddler.tags]
    tiddler.title = check_html(tiddler.title, environ)
    

def init(config):
    """
    init function
    """
    merge_config(config, VALIDATOR_CONFIG)
    
    TIDDLER_VALIDATORS.append(validate)

