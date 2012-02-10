from StringIO import StringIO
import datetime
import gzip
import json
import os
import urllib
import urllib2

class MediaWikiClient:
    """MediaWiki API client by Krenair"""
    def __init__(self, apiUrl, userAgent = ''):
        if 'http://' not in apiUrl:
            apiUrl = 'http://' + apiUrl #append http:// if it's not there already

        if 'api.php' in apiUrl:
            apiUrl = apiUrl
        elif apiUrl[-1:] == '/':
            apiUrl = apiUrl + 'api.php'
        else:
            apiUrl = apiUrl + '/api.php'

        response = urllib2.urlopen(urllib2.Request(apiUrl))
        if response.getcode() == 200:
            self.apiUrl = apiUrl
        else:
            raise Exception, 'Response to request for URL ' + request.geturl() + ': ' + response.getcode()

        if userAgent == '':
            pipe = os.popen('git log --pretty=format:"%H"')
            userAgent = 'PyMediaWikiClient/git/' + pipe.readline().strip()
            pipe.close()

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
        try:
            return json.loads(data)
        except ValueError as valueError:
            if valueError.message == 'No JSON object could be decoded':
                return data
            else:
                raise valueError

    def listToString(self, list):
        """Takes a list, outputs it as a pipe-separated string. Each of the list's elements should be convertable to a string."""
        if list.__class__ == str:
            return list

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
        self.userInfo = self.query(meta = ['userinfo'], extraParams = {'uiprop':self.listToString(properties)})['query']['userinfo']
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
            raise Exception, 'Maximum number of values 50 (500 for bots)'
        elif len(namespaces) <= 50:
            raise Exception, 'Maximum number of values 50 (500 for bots)'

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

    def feedWatchList(self, watchListOwner, format = 'rss', hours = 24, allRevisions = False, watchListToken = '', linkToDiffs = False):
        if format.lower() not in ['rss', 'atom']:
            raise Exception, 'Format must be RSS or atom'

        if int(hours) < 1 or int(hours) > 72:
            raise Exception, 'Hours must be between 1 and 72'

        values = {'action':'feedwatchlist', 'watchlistowner':watchListOwner, 'feedformat':format, 'hours':hours}

        if allRevisions:
            values['allrev'] = ''

        if watchListToken != '':
            values['watchlisttoken'] = watchListToken

        if linkToDiffs:
            values['linktodiffs'] = ''

        return self.apiRequest(values)

    def help(self):
        return self.apiRequest({})['error']['*']

    def paramInfo(self, modules = [], queryModules = [], mainModule = False, pageSetModule = False):
        if modules == [] and queryModules == [] and not mainModule and not pageSetModule:
            raise Exception, 'You must choose at least one parameter to use'

        values = {'action':'paraminfo'}

        if modules is not []:
            values['modules'] = self.listToString(modules)

        if queryModules is not []:
            values['querymodules'] = self.listToString(queryModules)

        if mainModule:
            values['mainmodule'] = ''

        if pageSetModule:
            values['pagesetmodule'] = ''

        return self.apiRequest(values)

    def rsd(self):
        return self.apiRequest({'action':'rsd'})

    def compare(self, fromTitle, fromRevision, toTitle, toRevision):
        return self.apiRequest({'action':'compare', 'fromtitle':fromTitle, 'fromrev':'fromRevision', 'totitle':toTitle, 'torev':toRevision})

    def purge(self, titles):
        return self.apiRequest({'action':'purge', 'titles':self.listToString(titles)})

    def rollback(self, title, user, summary = '', markBot = False):
        try:
            token = self.query(titles = title, extraParams = {'prop':'revisions', 'rvtoken':'rollback'})['query']['pages'].items()[0][1]['revisions'][0]['rollbacktoken']
        except KeyError as keyError:
            if keyError.message == 'rollbacktoken':
                raise APIError, 'You need to log in.'
            else:
                raise keyError

        values = {'action':'rollback', 'title':title, 'token':token, 'user':user}

        if summary != '':
            values['summary'] = summary

        if markBot:
            values['markbot'] = ''

        return self.apiRequest(values)

    def delete(self, title = None, pageId = None, reason = None, oldImage = None):
        #get a delete token
        try:
            token = self.query(titles = 'Main Page', extraParams = {'prop':'info', 'intoken':'delete'})['query']['pages']['1']['deletetoken']
        except KeyError as keyError:
            if keyError.message == 'deletetoken':
                raise APIError, 'You need to log in.'
            else:
                raise keyError

        #delete the page
        values = {'action':'delete', 'token':token}

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

    def unDelete(self, title, reason = '', timestamps = [], watchList = 'preferences'):
        try:
            token = self.query(titles = 'Main Page', extraParams = {'prop':'info', 'intoken':'edit'})['query']['pages']['1']['edittoken']
        except KeyError as keyError:
            if keyError.message == 'edittoken':
                raise APIError, 'You need to log in.'
            else:
                raise keyError
        values = {'action':'undelete', 'title':title, 'reason':reason, 'watchlist':watchList, 'token':token}

        if timestamps != []:
            values['timestamps'] = self.listToString(timestamps)

        return self.apiRequest(values)

    def protect(self, title, protections = {}, expiries = {}, reason = '', cascade = False):
        try:
            token = self.query(titles = 'Main Page', extraParams = {'prop':'info', 'intoken':'protect'})['query']['pages']['1']['protecttoken']
        except KeyError as keyError:
            if keyError.message == 'protecttoken':
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
            token = self.query(titles = 'Main Page', extraParams = {'prop':'info', 'intoken':'block'})['query']['pages']['1']['blocktoken']
        except KeyError as keyError:
            if keyError.message == 'blocktoken':
                raise APIError, 'You need to log in.'
            else:
                raise keyError

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

    def unBlock(self, _id = 0, user = '', reason = ''):
        values = {'action':'unblock'}
        if _id != 0:
            values['id'] = _id
        elif user != '':
            values['user'] = user
        else:
            raise Exception, 'You need to specify _id or user'

        try:
            values['token'] = self.query(titles = 'Main Page', extraParams = {'prop':'info', 'intoken':'unblock'})['query']['pages']['1']['unblocktoken']
        except KeyError as keyError:
            if keyError.message == 'unblocktoken':
                raise APIError, 'You need to log in.'
            else:
                raise keyError

        if reason != None:
            values['reason'] = reason

        return self.apiRequest(values)

    def move(self, to, _from = '', fromid = '', reason = '', movetalk = False, movesubpages = False, noredirect = False):
        try:
            token = self.query(titles = 'Main Page', extraParams = {'prop':'info', 'intoken':'move'})['query']['pages']['1']['movetoken']
        except KeyError as keyError:
            if keyError.message == 'movetoken':
                raise APIError, 'You need to log in.'
            else:
                raise keyError

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

    def fileRevert(self, fileName, comment = ''):
        try:
            token = self.query(titles = 'Main Page', extraParams = {'prop':'info', 'intoken':'edit'})['query']['pages']['1']['edittoken']
        except KeyError as keyError:
            if keyError.message == 'edittoken':
                raise APIError, 'You need to log in.'
            else:
                raise keyError
        archiveName = self.query(titles = 'File:' + fileName, extraParams = {'prop':'imageinfo', 'iiprop':'archivename', 'iilimit':2})['query']['pages'].items()[0][1]['imageinfo'][1]['archivename']
        values = {'action':'filerevert', 'filename':fileName, 'archivename':archiveName, 'token':token}

        if comment != '':
            values['comment'] = comment

        return self.apiRequest(values)

    def watch(self, title, unWatch = False):
        try:
            token = self.query(titles = 'Main Page', extraParams = {'prop':'info', 'intoken':'watch'})['query']['pages']['1']['watchtoken']
        except KeyError as keyError:
            if keyError.message == 'watchtoken':
                raise APIError, 'You need to log in.'
            else:
                raise keyError
        values = {'action':'watch', 'title':title, 'token':token}

        if unWatch:
            values['unwatch'] = ''

        return self.apiRequest(values)

    def patrol(self, rcid):
        try:
            token = self.query(list = 'recentchanges', extraParams = {'rctoken':'patrol', 'rclimit':'1'})['query']['recentchanges'][0]['patroltoken']
        except KeyError as keyError:
            if keyError.message == 'patroltoken':
                raise APIError, 'You may not patrol.'
            else:
                raise keyError
        return self.apiRequest({'action':'patrol', 'rcid':rcid, 'token':token})

    def _import(self):
        pass

    def userRights(self, user, add = [], remove = [], reason = None):
        token = self.query(list = 'users', extraParams = {'ususers':user, 'ustoken':'userrights'})['query']['users'][0]['userrightstoken']
        headers = {'action':'userrights', 'user':user, 'add':self.listToString(add), 'remove':self.listToString(remove), 'token':token}

        if reason is not None:
            headers['reason'] = reason

        return self.apiRequest({}, headers)

class APIError(Exception):
    #Base class for exceptions in this module
    pass
