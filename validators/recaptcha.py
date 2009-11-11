"""
Provide an Interface to the reCAPTCHA CAPTCHA tool. 

To use, you must sign up to reCAPTCHA at http://recaptcha.net/api/getkey

and add the following to tiddlywebconfig.py:

config={
    'recaptcha_private_key': '<private_key>'
}

substituting your private key into the field.

Then, put the following into your page:

<script type="text/javascript"
   src="http://api.recaptcha.net/challenge?k=<your_public_key>">
</script>

<noscript>
   <iframe src="http://api.recaptcha.net/noscript?k=<your_public_key>"
       height="300" width="500" frameborder="0"></iframe><br>
   <textarea name="recaptcha_challenge_field" rows="3" cols="40">
   </textarea>
   <input type="hidden" name="recaptcha_response_field" 
       value="manual_challenge">
</noscript>

Making sure to set the public key accordingly.

This will give you two FORM fields: recaptcha_challenge_field and 
recaptcha_response_field

When sending to TiddlyWeb, these must come through as tiddler fields 
(eg tiddler.fields['recaptcha_response_field']). They will then be deleted 
in this validator.
"""
from tiddlyweb.web.validator import TIDDLER_VALIDATORS, InvalidTiddlerError

import httplib2
import urllib

SERVER_URL = 'http://api-verify.recaptcha.net/verify'

def check_recaptcha(tiddler, environ):
    """
    validates a tiddler using the recaptcha api
    """
    #get required variables for POSTing to reCAPTCHA
    privatekey = environ['tiddlyweb.config']['recaptcha_private_key']
    remoteip = environ['REMOTE_ADDR']
    challenge = urllib.quote(tiddler.fields.get('recaptcha_challenge_field', \
        None))
    response = urllib.quote(tiddler.fields.get('recaptcha_response_field', \
        None))
    
    #make sure fields are present
    if not challenge:
        raise InvalidTiddlerError('recaptcha_challenge_field not found')
    if not response:
        raise InvalidTiddlerError('recaptcha_response_field not found')
    
    #send the request to reCAPTCHA
    postdata = 'privatekey=%s&remoteip=%s&challenge=%s&response=%s' % \
        (privatekey, remoteip, challenge, response)    
    http = httplib2.Http()
    response, content = http.request(SERVER_URL, method='POST', \
        headers={'Content-type': 'application/x-www-form-urlencoded'}, \
        body=postdata)
    
    if response['status'] != '200':
        raise InvalidTiddlerError('reCAPTCHA verification failed. Response ' \
            'code "%s" received.' % response)
            
    content = content.splitlines()
    result = content[0]
    if result == 'false':
        raise InvalidTiddlerError('reCAPTCHA verification failed. Please try ' \
            'again. Error message was "%s"' % content[1])
    
    #remove the CAPTCHA fields so they don't appear in the saved tiddler
    tiddler.fields.pop('recaptcha_challenge_field')
    tiddler.fields.pop('recaptcha_response_field')
    
    return tiddler

def init(config):
    """
    add the validator to the current list
    """
    TIDDLER_VALIDATORS.append(check_recaptcha)