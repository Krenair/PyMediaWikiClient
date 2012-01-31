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
        from StringIO import StringIO
        import gzip
        import json
        import urllib
        import urllib2
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
        out = ''
        for item in list:
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
                return True
            else:
                raise APIError, (result, "tokensent")
        elif result['result'] == 'Success':
            self.getUserInfo()
            self.isLoggedIn = True
            return True
        else:
            raise APIError, result

    def logout(self):
        if self.isLoggedIn:
            self.apiRequest({'action':'logout'})
            self.getUserInfo()
            return True
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

    def expandTemplates(self):
        pass

    def parse(self):
        pass

    def openSearch(self):
        pass

    def feedContributions(self):
        pass

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

    def purge(self):
        pass

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
            raise Error, "You must chose a title or a page ID."

        if reason != None:
            values['reason'] = reason

        if oldImage == True:
            values['oldimage'] = ''

        result = self.apiRequest(values)

    def undelete(self):
        pass

    def protect(self):
        pass

    def block(self, user, reason = None, expiry = "infinite", noCreate = True, noEmail = False, autoBlock = True, anonOnly = False):
        values = {'action':'block', 'user':user, 'expiry':expiry}
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
        result = self.apiRequest(values)

    def unblock(self):
        pass

    def move(self):
        pass

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
        result = self.apiRequest({}, headers)

class APIError(Exception):
    #Base class for exceptions in this module
    pass
