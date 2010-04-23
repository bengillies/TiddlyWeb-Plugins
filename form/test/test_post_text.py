"""
tests to ensure non binary tiddlers are inserted properly when POSTed
"""

from setup_test import setup_store, setup_web

from tiddlyweb.config import config
from tiddlyweb.model.tiddler import Tiddler
from tiddlyweb.model.bag import Bag
from tiddlyweb.store import NoTiddlerError

import httplib2

config['system_plugins'] = ['tiddlywebplugins.form']

def test_post_new_bag():
    """
    add a new tiddler to a bag
    """
    store = setup_store()
    setup_web()
    http = httplib2.Http()
    
    #make sure the tiddler we are inserting doesn't exist
    tiddler = Tiddler('HelloWorld', 'foo')
    try:
        store.get(tiddler)
        raise AssertionError('tiddler %s already exists' % tiddler.title)
    except NoTiddlerError:
        pass
    
    response = http.request('http://test_domain:8001/bags/foo/tiddlers',
        method='POST', 
        headers={'Content-type': 'application/x-www-form-urlencoded'},
        body='title=HelloWorld&text=Hi%20There')[0]
    assert response.status == 204
    
    #now check the tiddler is in the store
    try:
        store.get(tiddler)
    except NoTiddlerError:
        raise AssertionError('tiddler was not put into store')
    
    assert tiddler.title == 'HelloWorld'
    assert tiddler.text == 'Hi There'
    assert tiddler.tags == []

def test_post_new_recipe():
    """
    add a new tiddler to a recipe
    """
    store = setup_store()
    setup_web()
    http = httplib2.Http()
    
    #make sure the tiddler we are inserting doesn't exist
    tiddler = Tiddler('HelloWorld', 'bar')
    try:
        store.get(tiddler)
        raise AssertionError('tiddler %s already exists' % tiddler.title)
    except NoTiddlerError:
        pass
    
    response = http.request('http://test_domain:8001/recipes/foobar/tiddlers',
        method='POST', 
        headers={'Content-type': 'application/x-www-form-urlencoded'},
        body='title=HelloWorld&text=Hi%20There')[0]
    assert response.status == 204
    
    #now check the tiddler is in the store
    try:
        store.get(tiddler)
    except NoTiddlerError:
        raise AssertionError('tiddler was not put into store')
    
    assert tiddler.title == 'HelloWorld'
    assert tiddler.text == 'Hi There'
    assert tiddler.bag == 'bar'
    assert tiddler.tags == []

def test_post_existing():
    """
    overwrite an existing tiddler
    """
    store = setup_store()
    setup_web()
    http = httplib2.Http()
    
    #pre-add a tiddler
    tiddler = Tiddler('HelloWorld', 'foo')
    tiddler.text = 'Hi There'
    store.put(tiddler)
    
    response = http.request('http://test_domain:8001/bags/foo/tiddlers',
        method='POST', 
        headers={'Content-type': 'application/x-www-form-urlencoded'},
        body='title=HelloWorld&text=Changed%20Text')[0]
    assert response.status == 204
    
    #now check the tiddler is in the store and has been overwritten
    tiddler = Tiddler('HelloWorld', 'foo')
    try:
        store.get(tiddler)
    except NoTiddlerError:
        raise AssertionError('tiddler was not put into store')
    
    assert tiddler.title == 'HelloWorld'
    assert tiddler.text == 'Changed Text'
    assert tiddler.tags == []

def test_post_with_tags():
    """
    check that tags are properly entered
    """
    store = setup_store()
    setup_web()
    http = httplib2.Http()
    
    response = http.request('http://test_domain:8001/bags/foo/tiddlers',
        method='POST', 
        headers={'Content-type': 'application/x-www-form-urlencoded'},
        body='title=HelloWorld&text=Hi%20There&' \
            'tags=tag1%20tag2%20[[tag%20with%20spaces]]')[0]
    assert response.status == 204
    
    #now check the tiddler tags
    tiddler = Tiddler('HelloWorld', 'foo')
    try:
        store.get(tiddler)
    except NoTiddlerError:
        raise AssertionError('tiddler was not put into store')
    
    assert len(tiddler.tags) == 3
    for tag in ['tag1', 'tag2', 'tag with spaces']:
        assert tag in tiddler.tags

def test_post_no_title():
    """
    post a tiddler with no title set
    and make sure it gets into the store
    """
    store = setup_store()
    setup_web()
    http = httplib2.Http()
    
    #make sure there is nothing in bag 'foo'
    bag = Bag('foo')
    bag = store.get(bag)
    assert len(bag.list_tiddlers()) == 0
    
    response = http.request('http://test_domain:8001/bags/foo/tiddlers',
        method='POST', 
        headers={'Content-type': 'application/x-www-form-urlencoded'},
        body='text=Hi%20There')[0]
    assert response.status == 204
    
    #now find the tiddler just entered and check it
    bag = Bag('foo')
    bag = store.get(bag)
    tiddlers = bag.list_tiddlers()
    
    assert len(tiddlers) == 1
    
    tiddler = store.get(tiddlers[0])
    assert tiddler.title != ''
    assert tiddler.text == 'Hi There'

def test_post_multipart_mime_type():
    """
    test adding a tiddler with a multipart mime type
    """
    store = setup_store()
    setup_web()
    http = httplib2.Http()

    response = http.request('http://test_domain:8001/bags/foo/tiddlers',
        method='POST', 
        headers={'Content-type': 'multipart/form-data; ' \
                'boundary=---------------------------168072824752491622650073',
            'Content-Length': '283'},
        body='''-----------------------------168072824752491622650073
Content-Disposition: form-data; name="title"

HelloWorld
-----------------------------168072824752491622650073
Content-Disposition: form-data; name="text"

Hi There
-----------------------------168072824752491622650073--''')[0]
    assert response.status == 204

    #check the tiddler is in the store
    tiddler = Tiddler('HelloWorld', 'foo')
    try:
        store.get(tiddler)
    except NoTiddlerError:
        raise AssertionError('tiddler was not put into store')

    assert tiddler.title == 'HelloWorld'
    assert tiddler.text == 'Hi There'