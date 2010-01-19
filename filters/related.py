"""
Compare the given tiddler with other tiddlers in the bag and return 
anything that is related byt the supplied fields, sorted in order with most related first

eg: 

/bags/foo/tiddlers?related=bar:title,tags

will return all tiddlers related (by title and tags) to the tiddler "bar", ranked in most related first order

"""

from tiddlyweb.filters import FILTER_PARSERS, parse_for_filters, recursive_filter

import logging

import re


def compare_text(source, test):
    source_words = re.split('\W',source)
    count = 0
    for word in source_words:
        if word.lower() in test.lower():
            count += 1
            
    return count

def compare_tags(source, test):
    count = 0
    for tag in source:
        if tag in test:
            count += 1
            
    return count

def compare_fields(source, test, match):
    count = 0
    try:
        if type(source[match]) == text:
            count = compare_text(source[match], test[match])
    except KeyError:
        pass
            
    return count
                         
ATTRIBUTE_SELECTOR={
    'tags': compare_tags,
    }

def match_related_articles(title, matches, tiddlers): 
    def empty_generator(): return ;yield 'never'
    tiddlers = [tiddler for tiddler in tiddlers]
    try:
        source_tiddler = recursive_filter(parse_for_filters('select=title:%s' % title)[0], tiddlers).next()
    except StopIteration:
        #nothing to match on, so return an empty generator
        return empty_generator()
                         
    sort_set = []
    for tiddler in tiddlers: 
        count = 0
        for match in matches:
            try:
                source = getattr(source_tiddler, match)
                test = getattr(tiddler, match)
                test_func = ATTRIBUTE_SELECTOR.get(match, compare_text)
                count += test_func(source, test)
            except AttributeError:
                count += compare_fields(source_tiddler.fields, tiddler.fields, match)
                            
        if count > 0 and source_tiddler.title != tiddler.title:
            sort_set.append([tiddler,count])
    
    def sort_function(a,b): return cmp(b[1],a[1]) 
    sort_set.sort(sort_function)
    
    result = (tiddler_set[0] for tiddler_set in sort_set)
    
    return result



def related_parse(command):
    
    attribute, args = command.split(':', 1)
    args = args.split(',')
    
    def relator(tiddlers, indexable=False, environ=None):
        return match_related_articles(attribute, args, tiddlers)
    
    return relator


FILTER_PARSERS['related'] = related_parse
        
def init(config):
    pass