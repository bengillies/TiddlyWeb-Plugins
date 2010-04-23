"""
checks to ensure that all urls have been set up properly 
and POST has been added to all the correct places
"""
from tiddlyweb.config import config

from setup_test import setup_store, setup_web
from tiddlywebplugins import form

import httplib2

def reset_config():
    """
    reset the plugin and prefix info in config
    ready for next call
    """
    config['system_plugins'] = []
    config['server_prefix'] = ''
    

def test_override_bag_url():
    """
    check that the /bags/bagname/tiddlers url has been found
    and POST support added
    """
    reset_config()
    setup_store()
    setup_web()
    http = httplib2.Http()
    
    #verify that POST is not available
    response = http.request('http://test_domain:8001/bags/foo/tiddlers',
        method='POST')[0]
    assert response.status == 405
    
    #restart the server with the form plugin in place
    config['system_plugins'] = ['tiddlywebplugins.form']
    setup_web()
    
    #now verify that POST support has been added
    response = http.request('http://test_domain:8001/bags/foo/tiddlers',
        method='POST', 
        headers={'Content-type': 'application/x-www-form-urlencoded'},
        body='title=HelloWorld&text=Hi%20There')[0]
    assert response.status == 204
    
def test_override_recipe_url():
    """
    check that the /recipes/recipename/tidlers url has been found
    and POST support added
    """
    reset_config()
    setup_store()
    setup_web()
    http = httplib2.Http()
    
    #verify that POST is not available
    response = http.request('http://test_domain:8001/recipes/foobar/tiddlers',
        method='POST')[0]
    assert response.status == 405
    
    #restart the server with the form plugin in place
    config['system_plugins'] = ['tiddlywebplugins.form']
    setup_web()
    
    #now verify that POST support has been added
    response = http.request('http://test_domain:8001/recipes/foobar/tiddlers',
        method='POST', 
        headers={'Content-type': 'application/x-www-form-urlencoded'},
        body='title=HelloWorld&text=Hi%20There')[0]
    assert response.status == 204
    
def test_override_server_prefix():
    """
    test that the overriding works when a server prefix is present
    """
    reset_config()
    config['server_prefix'] = '/prefix'
    setup_store()
    setup_web()
    http = httplib2.Http()
    
    #verify that POST is not available
    response = http.request('http://test_domain:8001/prefix/bags/foo/tiddlers',
        method='POST')[0]
    assert response.status == 405
    
    #restart the server with the form plugin in place
    config['system_plugins'] = ['tiddlywebplugins.form']
    setup_web()
    
    #now verify that POST support has been added
    response = http.request('http://test_domain:8001/prefix/bags/foo/tiddlers',
        method='POST', 
        headers={'Content-type': 'application/x-www-form-urlencoded'},
        body='title=HelloWorld&text=Hi%20There')[0]
    assert response.status == 204