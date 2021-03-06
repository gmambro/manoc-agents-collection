import urllib2
import base64
import json as json_module

class PreemptiveBasicAuthHandler(urllib2.HTTPBasicAuthHandler):
    '''Preemptive basic auth.

    Instead of waiting for a 403 to then retry with the credentials,
    send the credentials if the url is handled by the password manager.
    Note: please use realm=None when calling add_password.'''

    def http_request(self, req):
        url = req.get_full_url()
        realm = None
        # this is very similar to the code from retry_http_basic_auth()
        # but returns a request object.
        user, pw = self.passwd.find_user_password(realm, url)
        if pw:
            raw = "%s:%s" % (user, pw)
            auth = 'Basic %s' % base64.b64encode(raw).strip()
            req.add_unredirected_header(self.auth_header, auth)
        return req

    https_request = http_request
    

class RequestError(Exception):
    """A generic Exception while processing the request."""

    response = None
    request = None
    def __init__(self, *args, **kwargs):        
        self.response = kwargs.pop('response', None)
        self.request = kwargs.pop('request', None)
        if self.response is not None and self.request is None:
            if hasattr(self.response, 'request'):
                self.request = self.response.request            
        super(RequestError, self).__init__(*args, **kwargs)       

    def __str__(self):
        msg = "RequestError"
        if self.request:
            msg = msg + " request="+str(self.request)
        if self.response:
            msg = msg + " response="+str(self.response)
        return msg
            
class HTTPError(RequestError):
    """An HTTP error occurred."""
    pass
    
class Response():
    
    def __init__(self, method=None, url=None, headers=None,
                 data=None, params=None, auth=None, json=None):

        # defaults
        method = method.upper()
        headers = {} if headers is None else headers
        params = {} if params is None else params

        body = None
        content_type = None
        if not data and json is not None:
            content_type = 'application/json'
            data = json_module.dumps(json)

        # Add content-type if it wasn't explicitly provided.
        if content_type and ('content-type' not in headers):
            headers['Content-Type'] = content_type

        req = urllib2.Request(url, headers=headers)
        if data:
            req.add_data(data)
        
        if auth is not None:
            password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
            password_manager.add_password(None, url, auth[0], auth[1])
 
            auth_manager = PreemptiveBasicAuthHandler(password_manager)
            opener = urllib2.build_opener(auth_manager).open
        else:
            opener = urllib2.urlopen
            
        self.request = req
        self._opener = opener
        self._code = None
        self._data = None
        self._is_error = False
        self._handler = None  
        self._raise_on_http_error = False
        
    def raise_on_http_error(self):
        self._raise_on_http_error = True
        
    def code(self):
        if self._code:
            return self._code

        self.read()
        return self._code
            
    def header(self, name):
        return self._handler.headers.getheader(name) 
        
    def read(self):
        if self._is_error:
            return None
        if self._data is None:
            try:
                self._handler = self._opener(self.request)
                self._data = self._handler.read()
                self._code = self._handler.getcode()
            except urllib2.HTTPError as e:
                self._code = e.code 
                self._is_error = True
                raise HTTPError(response=self)
            except:
                self._is_error = True
                raise
            if self._raise_on_http_error and self._handler.getcode() != 200:
                raise HTTPError(response=self)
        return self._data        
    
    def json(self):        
        return json_module.loads(self.read()) 

    def data(self):
        return self.read()
    
def GET(url, **kwargs):
    return Response('get', url, **kwargs)

def POST(url, data=None, json=None,  **kwargs):
    return Response('post', url, data=data, json=json, **kwargs)

