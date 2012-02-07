from StringIO import StringIO
import datetime
import gzip
import json
import urllib
import urllib2

class MediaWikiClient:
    """MediaWiki API client by Krenair"""
    def __init__(self, apiUrl, userAgent = 'PyMediaWikiClient/0.1'):
        self.apiUrl = apiUrl
        self.userAgent = userAgent
        self.cookieInfo = None
        self.isLoggedIn = False
        self.getUserInfo()

    def apiRequest(self, values, headers = {}, urlExtras = ''):
        """Handles all requests to MediaWiki"""
        values['format'] = 'json'
        headers['Accept-Encoding'] = 'gzip'
        headers['User-Agent'] = self.userAgent
        if self.cookieInfo is not None:
            headers['Cookie'] = self.cookieInfo
        response = urllib2.urlopen(urllib2.Request(self.apiUrl + urlExtras, urllib.urlencode(values), headers))
        if response.info().get('Content-Encoding') == 'gzip':
            data = gzip.GzipFile(fileobj=StringIO(response.read())).read()
        else:
            data = response.read()
        return json.loads(data)

    def listToString(self, list):
        """Takes a list, outputs it as a pipe-separated string. Each of the list's elements should be convertable to a string."""
        out = ''
        for item in list:
            try:
                item = str(item)
            except:
                raise Exception, 'Item was not able to be converted to a string'
            out += (item + '|')
        return out[:-1]

    def getUserInfo(self):
        properties = ['blockinfo', 'hasmsg', 'groups', 'implicitgroups', 'rights', 'changeablegroups', 'editcount', 'ratelimits', 'email', 'registrationdate']
        result = self.query(meta = ['userinfo'], extraParams = {'uiprop':self.listToString(properties)})
        self.userInfo = result['query']['userinfo']
        return self.userInfo

    def login(self, username, password):
        self.username = username
        #get login token
        result = self.apiRequest({'action':'login', 'lgname':username, 'lgpassword':password, 'format':'json'})
        self.cookieInfo = result['login']['cookieprefix'] + '_session=' + result['login']['sessionid']
        if result['login']['result'] == 'NeedToken':
            #confirm login token
            result = self.apiRequest({'action':'login', 'lgname':username, 'lgpassword':password, 'format':'json', 'lgtoken':result['login']['token']})
            if result['login']['result'] == 'Success':
                self.getUserInfo()
                self.isLoggedIn = True
                return
            else:
                raise APIError, (result, "tokensent")
        elif result['result'] == 'Success':
            self.getUserInfo()
            self.isLoggedIn = True
            return
        else:
            raise APIError, result

    def logout(self):
        if self.isLoggedIn:
            self.apiRequest({'action':'logout'})
            self.getUserInfo()
            return
        else:
            raise Exception, "Not logged in."

    def query(self, titles = [], pageIds = [], revIds = [], list = [], meta = [], generator = '', redirects = True, convertTitles = False, indexPageIds = False, export = False, exportNoWrap = False, iwUrl = False, extraParams = {}):
        values = {'action':'query'}
        if titles != []:
            values['titles'] = self.listToString(titles)
        elif pageIds != []:
            values['pageids'] = self.listToString(pageIds)
        elif revIds != []:
            values['revids'] = self.listToString(revIds)
        elif list != []:
            values['list'] = self.listToString(list)
        elif meta != []:
            values['meta'] = self.listToString(meta)

        for key, value in extraParams.items():
            values[key] = value

        if generator != '':
            values['generator'] = generator

        if redirects == True:
            values['redirects'] = ''

        if convertTitles == True:
            values['converttitles'] = ''

        if indexPageIds == True:
            values['indexpageids'] = ''

        if export == True:
            values['export'] = ''

        if exportNoWrap == True:
            values['exportnowrap'] = ''

        if iwUrl == True:
            values['iwurl'] = ''

        return self.apiRequest(values)

    def expandTemplates(self, text, title = 'API', generateXml = False, includeComments = False):
        values = {'action':'expandtemplates', 'text':text, 'title':title}
        if generateXml:
            values['generatexml'] = ''

        if includeComments:
            values['includecomments'] = ''

        return self.apiRequest(values)

    def parse(self):
        pass

    def openSearch(self, search, limit = 10, namespaces = [0]):
        if 'bot' in self.userInfo['groups'] and len(namespaces) <= 500:
            return False #Maximum number of values 50 (500 for bots)
        elif len(namespaces) <= 50:
            return False #Maximum number of values 50 (500 for bots)

        return self.apiRequest({'action':'opensearch', 'search':search, 'limit':limit, 'namespace':self.listToString(namespaces)})

    def feedContributions(self, user, feedFormat = 'rss', namespaces = [0], year = datetime.datetime.now().year, month = datetime.datetime.now().month, tagFilter = [], deletedOnly = False, topOnly = False, showSizeDiff = False):
        if feedFormat not in ['rss', 'atom']:
            raise Exception, "bad feedFormat: " + feedFormat

        values = {'action':'feedcontributions', 'feedformat':feedFormat, 'user':user, 'namespace':self.listToString(namespaces), 'year':year, 'month':month}

        if tagFilter != []:
            values['tagfilter'] = self.listToString(tagFilter)

        if deletedOnly:
            values['deletedonly'] = ''

        if topOnly:
            values['toponly'] = ''

        if showSizeDiff:
            values['showsizediff'] = ''

        return self.apiRequest(values)

    def feedWatchlist(self):
        pass

    def help(self):
        pass

    def paramInfo(self):
        pass

    def rsd(self):
        pass

    def compare(self):
        pass

    def purge(self, titles):
        return self.apiRequest({'action':'purge', 'titles':self.listToString(titles)})

    def rollback(self):
        pass

    def delete(self, title = None, pageId = None, reason = None, oldImage = None):
        #get a delete token
        result = self.apiRequest({'action':'query', 'prop':'info', 'intoken':'delete', 'titles':'Main Page'})

        #delete the page
        values = {'action':'delete', 'token':result['query']['pages']['1']['deletetoken']}
        if title != None:
            values['title'] = title
        elif pageId != None:
            values['pageid'] = pageId
        else:
            raise Exception, "You must chose a title or a page ID."

        if reason != None:
            values['reason'] = reason

        if oldImage == True:
            values['oldimage'] = ''

        return self.apiRequest(values)

    def undelete(self):
        pass

    def protect(self, title, protections = {}, expiries = {}, reason = '', cascade = False):
        try:
            token = self.apiRequest({'action':'query', 'prop':'info', 'intoken':'protect', 'titles':'Main Page'})['query']['pages']['1']['protecttoken']
        except KeyError as keyerror:
            if keyerror.message == 'protecttoken':
                raise APIError, 'You need to log in.'

        values = {'action':'protect', 'title':title, 'token':token}

        if 'edit' not in protections.keys():
            protections['edit'] = 'all'

        if 'move' not in protections.keys():
            protections['move'] = 'all'

        if 'edit' not in expiries.keys():
            expiries['edit'] = 'infinite'

        if 'move' not in expiries.keys():
            expiries['move'] = 'infinite'

        values['protections'] = 'edit=' + protections['edit'] + '|move=' + protections['move']
        values['expiry'] = expiries['edit'] + '|' + expiries['move']

        if reason != '':
            values['reason'] = ''

        if cascade:
            values['cascade'] = ''

        return self.apiRequest(values)

    def block(self, user, reason = None, expiry = "infinite", noCreate = True, noEmail = False, autoBlock = True, anonOnly = False):
        try:
            token = self.apiRequest({'action':'query', 'prop':'info', 'intoken':'block', 'titles':'Main Page'})['query']['pages']['1']['blocktoken']
        except KeyError as keyerror:
            if keyerror.message == 'blocktoken':
                raise APIError, 'You need to log in.'
            else:
                raise keyerror

        values = {'action':'block', 'user':user, 'expiry':expiry, 'token':token}
        if noCreate == True:
            values['nocreate'] = ''

        if noEmail == True:
            values['noemail'] = ''

        if autoBlock == True:
            values['autoblock'] = ''

        if anonOnly == True:
            values['anononly'] = ''

        if reason != None:
            values['reason'] = reason
        return self.apiRequest(values)

    def unblock(self, _id = 0, user = '', reason = ''):
        values = {'action':'unblock'}
        if _id != 0:
            values['id'] = _id
        elif user != '':
            values['user'] = user
        else:
            raise Exception, 'You need to specify _id or user'

        try:
            values['token'] = self.apiRequest({'action':'query', 'prop':'info', 'intoken':'unblock', 'titles':'Main Page'})['query']['pages']['1']['unblocktoken']
        except KeyError as keyerror:
            if keyerror.message == 'unblocktoken':
                raise APIError, 'You need to log in.'
            else:
                raise keyerror

        if reason != None:
            values['reason'] = reason
        return self.apiRequest(values)

    def move(self, to, _from = '', fromid = '', reason = '', movetalk = False, movesubpages = False, noredirect = False):
        try:
            token = self.apiRequest({'action':'query', 'prop':'info', 'intoken':'move', 'titles':'Main Page'})['query']['pages']['1']['movetoken']
        except KeyError as keyerror:
            if keyerror.message == 'movetoken':
                raise APIError, 'You need to log in.'
            else:
                raise keyerror
        values = {'action':'move', 'to':to, 'token':token}
        if _from != '':
            values['from'] = _from
        elif fromid != '':
            values['fromid'] = fromid
        else:
            raise Exception, 'You need to specify _from or fromid'

        if reason != '':
            values['reason'] = reason

        if movetalk:
            values['movetalk'] = ''

        if movesubpages:
            values['movesubpages'] = ''

        if noredirect:
            values['noredirect'] = ''
        return self.apiRequest(values)

    def edit(self):
        pass

    def upload(self):
        pass

    def filerevert(self):
        pass

    def watch(self):
        pass

    def patrol(self):
        pass

    def _import(self):
        pass

    def userrights(self, user, add = [], remove = [], reason = None):
        values = {'action':'query', 'list':'users', 'ususers':user, 'ustoken':'userrights'}
        token = self.apiRequest(values)['query']['users'][0]['userrightstoken']

        headers = {'action':'userrights', 'user':user, 'add':self.listToString(add), 'remove':self.listToString(remove), 'token':token}
        if reason is not None:
            headers['reason'] = reason
        return self.apiRequest({}, headers)

class APIError(Exception):
    #Base class for exceptions in this module
    pass
