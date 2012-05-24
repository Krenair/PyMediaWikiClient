import gzip, json, os
try: # Python 3
    from http.cookiejar import CookieJar
    from io import StringIO
    from urllib.parse import urlencode
    from urllib.error import HTTPError
    from urllib.request import urlopen
    from urllib.request import build_opener
    from urllib.request import install_opener
    from urllib.request import Request
    from urllib.request import HTTPCookieProcessor
except ImportError: # Python 2
    from cookielib import CookieJar
    from StringIO import StringIO
    from urllib import urlencode
    from urllib2 import HTTPError
    from urllib2 import urlopen
    from urllib2 import build_opener
    from urllib2 import install_opener
    from urllib2 import Request
    from urllib2 import HTTPCookieProcessor

class MediaWikiClient:
    """MediaWiki API client by Krenair"""
    def __init__(self, url, userAgent = '', cookieJar = CookieJar(), maxlag = 5):
        if 'http://' not in url and 'https://' not in url:
            url = 'http://' + url # Append http:// if it's not there already.

        if 'api.php' in url:
            apiUrl = url
            indexUrl = url[:-7] + 'index.php'
        elif 'index.php' in url:
            indexUrl = url
            apiUrl = url[:-9] + 'api.php'
        elif url[-1:] == '/':
            indexUrl = url + 'index.php'
            apiUrl = url + 'api.php'
        else:
            indexUrl = url + '/index.php'
            apiUrl = url + '/api.php'

        try:
            response = urlopen(Request(apiUrl))
            self.apiUrl = apiUrl
            #response = urlopen(Request(indexUrl))
            self.indexUrl = indexUrl
        except HTTPError as e:
            e.msg += ' - URL: ' + e.geturl()
            raise e

        if userAgent == '':
            pipe = os.popen('git log --pretty=format:"%H"')
            userAgent = 'PyMediaWikiClient/git/' + pipe.readline().strip()
            pipe.close()

        self.userAgent = userAgent
        self.cookieJar = cookieJar
        self.maxlagDefault = maxlag
        install_opener(build_opener(HTTPCookieProcessor(self.cookieJar)))
        self.isLoggedIn = False
        self.getUserInfo()
        try:
            self.getEditToken(cached = False)
        except:
            pass

    def apiRequest(self, values, headers = {}, urlExtras = ''):
        """Handles all requests to MediaWiki"""
        values['format'] = 'json'

        if 'maxlag' not in values:
            values['maxlag'] = self.maxlagDefault

        for key, value in list(values.items()):
            if value.__class__ == list:
                values[key] = self.listToString(value)

        headers['Accept-Encoding'] = 'gzip'
        headers['User-Agent'] = self.userAgent
        response = urlopen(Request(self.apiUrl + urlExtras, urlencode(values), headers))

        if response.info().get('Content-Encoding') == 'gzip':
            data = gzip.GzipFile(fileobj=StringIO(response.read())).read()
        else:
            data = response.read()

        try:
            result = json.loads(data)
        except ValueError as valueError:
            if valueError.message == 'No JSON object could be decoded':
                result = data
            else:
                raise valueError

        if 'error' in result:
            raise APIError(result['error'])
        else:
            return result

    def indexRequest(self, values, headers = {}, urlExtras = ''):
        headers['Accept-Encoding'] = 'gzip'
        headers['User-Agent'] = self.userAgent
        response = urlopen(Request(self.indexUrl + urlExtras, urlencode(values), headers))

        if response.info().get('Content-Encoding') == 'gzip':
            return gzip.GzipFile(fileobj=StringIO(response.read())).read()
        else:
            return response.read()

    def listToString(self, items):
        """Takes a list, outputs it as a pipe-separated string. The list should be convertable to a set and each of the list's elements should be convertable to a string."""
        items = sorted(list(set(items))) #remove duplicates and sort
        out = ''
        for item in items:
            try:
                item = str(item)
            except:
                raise Exception('Item was not able to be converted to a string')
            out += (item + '|')

        return out[:-1]

    def getUserInfo(self):
        """Gets information about you."""
        properties = ['blockinfo', 'changeablegroups', 'editcount', 'email', 'groups', 'hasmsg', 'implicitgroups', 'ratelimits', 'registrationdate', 'rights']
        self.userInfo = self.apiRequest({'action':'query', 'meta':'userinfo', 'uiprop':properties})['query']['userinfo']
        return self.userInfo

    def login(self, username, password):
        """Logs you in."""
        #get login token
        result = self.apiRequest({'action':'login', 'lgname':username, 'lgpassword':password})
        if result['login']['result'] == 'NeedToken':
            #confirm login token
            result = self.apiRequest({'action':'login', 'lgname':username, 'lgpassword':password, 'lgtoken':result['login']['token']})
            if result['login']['result'] == 'Success':
                self.getUserInfo()
                self.getEditToken(cached = False)
                self.isLoggedIn = True
            else:
                raise APIError(result)
        else:
            raise APIError(result)

    def logout(self):
        """Logs you out."""
        if self.isLoggedIn:
            self.apiRequest({'action':'logout'})
            self.getUserInfo()
            self.getEditToken(cached = False)
        else:
            raise Exception('Not logged in.')

    def getEditToken(self, cached = True):
        """Gets your edit token."""
        if 'editToken' in dir(self) and cached:
            return self.editToken

        try:
            self.editToken = list(self.apiRequest({'action':'query', 'titles':'Main Page', 'prop':'info', 'intoken':'edit'})['query']['pages'].values())[0]['edittoken']
            #self.editToken = self.apiRequest({'action':'tokens', 'type':'edit'})['tokens']['edittoken']
            return self.editToken
        except KeyError as keyError:
            if keyError.message == 'edittoken':
                raise APIError('You may not edit.')
            else:
                raise keyError

    def fetchPageContents(self, page):
        return self.indexRequest({'action':'raw', 'title':page})

class APIError(Exception):
    #Base class for exceptions in this module
    pass
