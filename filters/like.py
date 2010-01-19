"""
Compare the given string to the supplied field and return everything that partially matches:

eg:

/bags/foo/tiddlers?like=title:bar

will return all tiddlers where bar is contained somewhere within the title

"""

from tiddlyweb.filters import FILTER_PARSERS
from tiddlyweb.filters.select import select_parse





def compare_text(source, test, negate=False):
    if source.lower() in test.lower():
        return True != negate
            
    return False != negate

def compare_tags(source, test, negate=False):
    count = 0
    for tag in test:
        if source.lower() in tag.lower():
            return True != negate
            
    return False != negate

def compare_fields(source, test, attribute, negate=False):
    try:
        if type(test[attribute]) == text:
            return compare_text(source[attribute], test[attribute])
    except KeyError:
        return False != negate
            
    return False != negate
                         
ATTRIBUTE_SELECTOR={
    'tags': compare_tags,
    }


def like(attribute, args, tiddlers, negate=False):
    for tiddler in tiddlers:
        try:
            test = getattr(tiddler, attribute)
            test_func = ATTRIBUTE_SELECTOR.get(attribute, compare_text)
            found = test_func(args, test, negate)
        except AttributeError:
            found = compare_fields(args, tiddler.fields, attribute, negate)
            
        if found:
            yield tiddler
    
    return 
 
 
def like_parse(command):
    attribute, args = command.split(':', 1)
    
    if args.startswith('!'):
        args = args.replace('!', '', 1)
        def selector(tiddlers, indexable=False, environ=None):
            return like(attribute, args, tiddlers, negate=True)
    else:    
        def selector(tiddlers, indexable=False, environ=None):
            return like(attribute, args, tiddlers)
            
    return selector
 
 
FILTER_PARSERS['like'] = like_parse
 
 
def init(config):
    pass
