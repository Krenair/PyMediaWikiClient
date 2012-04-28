from cookielib import CookieJar
from StringIO import StringIO
import datetime
import gzip
import hashlib
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
            pass
        elif apiUrl[-1:] == '/':
            apiUrl += 'api.php'
        else:
            apiUrl += '/api.php'

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
        self.cookieJar = CookieJar()
        urllib2.install_opener(urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookieJar)))
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
            values['maxlag'] = '5'
        for key, value in values.items():
            if value.__class__ == list:
                values[key] = self.listToString(value)

        headers['Accept-Encoding'] = 'gzip'
        headers['User-Agent'] = self.userAgent
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

    def listToString(self, items):
        """Takes a list, outputs it as a pipe-separated string. The list should be convertable to a set and each of the list's elements should be convertable to a string."""
        items = sorted(list(set(items))) #remove duplicates and sort
        out = ''
        for item in items:
            try:
                item = str(item)
            except:
                raise Exception, 'Item was not able to be converted to a string'
            out += (item + '|')

        return out[:-1]

    def getUserInfo(self):
        properties = ['blockinfo', 'changeablegroups', 'editcount', 'email', 'groups', 'hasmsg', 'implicitgroups', 'ratelimits', 'registrationdate', 'rights']
        self.userInfo = self.query(meta = ['userinfo'], extraParams = {'uiprop':properties})['query']['userinfo']
        return self.userInfo

    def login(self, username, password):
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
                raise APIError, result
        else:
            raise APIError, result

    def logout(self):
        if self.isLoggedIn:
            self.apiRequest({'action':'logout'})
            self.getUserInfo()
            self.getEditToken(cached = False)
        else:
            raise Exception, 'Not logged in.'

    def query(self, titles = [], pageIds = [], revIds = [], _list = [], meta = [], generator = '', redirects = True, convertTitles = False, indexPageIds = False, export = False, exportNoWrap = False, iwUrl = False, extraParams = {}):
        #TODO: Add some methods to allow a better way of interacting with the query module.
        values = {'action':'query'}
        if titles != []:
            values['titles'] = titles
        elif pageIds != []:
            values['pageids'] = pageIds
        elif revIds != []:
            values['revids'] = revIds
        elif _list != []:
            values['list'] = _list
        elif meta != []:
            values['meta'] = meta

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

    def getEditToken(self, cached = True):
        """Gets your edit token."""
        if 'editToken' in dir(self) and cached:
            return self.editToken

        try:
            self.editToken = self.query(titles = 'Main Page', extraParams = {'prop':'info', 'intoken':'edit'})['query']['pages'].values()[0]['edittoken']
            return self.editToken
        except KeyError as keyError:
            if keyError.message == 'edittoken':
                raise APIError, 'You may not edit.'
            else:
                raise keyError

    def expandTemplates(self, text, title = 'API', generateXml = False, includeComments = False):
        values = {'action':'expandtemplates', 'text':text, 'title':title}
        if generateXml:
            values['generatexml'] = ''

        if includeComments:
            values['includecomments'] = ''

        return self.apiRequest(values)

    def parse(self, title = 'API', text = '', summary = '', page = '', pageId = '', redirects = False, oldId = None, prop = 'text|langlinks|categories|links|templates|images|externallinks|sections|revid|displaytitle', pst = False, onlyPst = False, useLang = None, section = '', disablePP = False):
        values = {'action':'parse', 'title':title, 'text':text, 'summary':summary, 'prop':prop}

        if page != '':
            values['page'] = page
            del values['text'], values['title']

        if pageId != '':
            values['pageid'] = pageId
            try:
                del values['text'], values['title']
            except KeyError as keyError:
                pass

        if redirects:
            values['redirects'] = ''

        if oldId != None:
            values['oldid'] = oldId

        if pst:
            values['pst'] = ''

        if onlyPst:
            values['onlypst'] = ''

        if useLang != None:
            values['uselang'] = useLang

        if section != '':
            values['section'] = section

        if disablePP:
            values['disablepp'] = ''

        return self.apiRequest(values)

    def openSearch(self, search, limit = 10, namespaces = [0]):
        if 'bot' in self.userInfo['groups'] and len(namespaces) <= 500:
            raise Exception, 'Maximum number of values 50 (500 for bots)'
        elif len(namespaces) <= 50:
            raise Exception, 'Maximum number of values 50 (500 for bots)'

        return self.apiRequest({'action':'opensearch', 'search':search, 'limit':limit, 'namespace':namespaces})

    def feedContributions(self, user, feedFormat = 'rss', namespaces = [0], year = datetime.datetime.now().year, month = datetime.datetime.now().month, tagFilter = [], deletedOnly = False, topOnly = False, showSizeDiff = False):
        if feedFormat not in ['rss', 'atom']:
            raise Exception, 'Bad feedFormat: ' + feedFormat

        values = {'action':'feedcontributions', 'feedformat':feedFormat, 'user':user, 'namespace':namespaces, 'year':year, 'month':month}

        if tagFilter != []:
            values['tagfilter'] = tagFilter

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
            values['modules'] = modules

        if queryModules is not []:
            values['querymodules'] = queryModules

        if mainModule:
            values['mainmodule'] = ''

        if pageSetModule:
            values['pagesetmodule'] = ''

        return self.apiRequest(values)

    def rsd(self):
        return self.apiRequest({'action':'rsd'})

    def compare(self, fromTitle = '', fromRevision = '', fromId = '', toTitle = '', toRevision = '', toId = ''):
        if fromTitle == '' and fromRevision == '' and fromId == '':
            raise Exception, 'You must supply fromTitle, fromRevision, or fromId.'
        elif toTitle == '' and toRevision == '' and toId == '':
            raise Exception, 'You must supply toTitle, toRevision, or toId.'

        return self.apiRequest({'action':'compare', 'fromtitle':fromTitle, 'fromrev':fromRevision, 'fromid':fromId, 'totitle':toTitle, 'torev':toRevision, 'toid':toId})

    def purge(self, titles):
        return self.apiRequest({'action':'purge', 'titles':titles})

    def rollback(self, title, user, summary = '', markBot = False):
        try:
            token = self.query(titles = title, extraParams = {'prop':'revisions', 'rvtoken':'rollback'})['query']['pages'].items()[0][1]['revisions'][0]['rollbacktoken']
        except KeyError as keyError:
            if keyError.message == 'rollbacktoken':
                raise APIError, 'You may not rollback.'
            else:
                raise keyError

        values = {'action':'rollback', 'title':title, 'token':token, 'user':user}

        if summary != '':
            values['summary'] = summary

        if markBot:
            values['markbot'] = ''

        return self.apiRequest(values)

    def delete(self, title = None, pageId = None, reason = None, oldImage = None):
        values = {'action':'delete', 'token':self.getEditToken()}

        if title != None:
            values['title'] = title
        elif pageId != None:
            values['pageid'] = pageId
        else:
            raise Exception, 'You must chose a title or a page ID.'

        if reason != None:
            values['reason'] = reason

        if oldImage == True:
            values['oldimage'] = ''

        return self.apiRequest(values)

    def unDelete(self, title, reason = '', timestamps = [], watchList = 'preferences'):
        values = {'action':'undelete', 'title':title, 'reason':reason, 'watchlist':watchList, 'token':self.getEditToken()}

        if timestamps != []:
            values['timestamps'] = timestamps

        return self.apiRequest(values)

    def protect(self, title, protections = {}, expiries = {}, reason = '', cascade = False):
        values = {'action':'protect', 'title':title, 'token':self.getEditToken()}

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

    def block(self, user, reason = None, expiry = 'infinite', noCreate = True, noEmail = False, autoBlock = True, anonOnly = False):
        values = {'action':'block', 'user':user, 'expiry':expiry, 'token':self.getEditToken()}
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
            values['token'] = self.query(titles = 'Main Page', extraParams = {'prop':'info', 'intoken':'unblock'})['query']['pages'].values()[0]['unblocktoken']
        except KeyError as keyError:
            if keyError.message == 'unblocktoken':
                raise APIError, 'You may not unblock.'
            else:
                raise keyError

        if reason != None:
            values['reason'] = reason

        return self.apiRequest(values)

    def move(self, to, _from = '', fromid = '', reason = '', movetalk = False, movesubpages = False, noredirect = False):
        values = {'action':'move', 'to':to, 'token':self.getEditToken()}

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

    def edit(self, title, text = '', section = None, summary = '', minor = False, notMinor = False, bot = False, baseTimestamp = None, startTimestamp = None, recreate = False, createOnly = False, noCreate = False, watchList = 'preferences', md5 = '', captchaId = None, captchaWord = None, undo = '', undoAfter = False):
        if watchList not in ['watch', 'unwatch', 'preferences', 'nochange']:
            raise Exception, 'watchList must be watch, unwatch, preferences or nochange.'

        values = {'action':'edit', 'title':title, 'watchlist':watchList, 'token':self.getEditToken()}

        if section != None:
            values['section'] = section

        if minor:
            values['minor'] = ''

        if notMinor:
            values['notminor'] = ''

        if bot:
            values['bot'] = ''

        if baseTimestamp != None:
            values['basetimestamp'] = baseTimestamp

        if startTimestamp != None:
            values['starttimestamp'] = startTimestamp

        if recreate:
            values['recreate'] = ''

        if createOnly:
            values['createonly'] = ''

        if noCreate:
            values['nocreate'] = ''

        if md5 == '':
            values['md5'] = hashlib.md5(text).hexdigest()
        else:
            values['md5'] = md5

        if captchaId != None:
            values['captchaid'] = captchaId

        if captchaWord != None:
            values['captchaword'] = captchaWord

        if undo != '':
            values['undo'] = undo

        if undoAfter:
            values['undoafter'] = ''

        return self.apiRequest(values)

    def upload(self, fileName, comment, url, text = '', watch = False, ignoreWarnings = False, sessionKey = None, asyncDownload = False):
        """Currently restricted to URLs only. See https://github.com/Krenair/PyMediaWikiClient/issues/1"""
        values = {'action':'upload', 'filename':fileName, 'comment':comment, 'url':url, 'token':self.getEditToken()}

        if text != '':
            values['text'] = text

        if watch:
            values['watch'] = ''

        if ignoreWarnings:
            values['ignorewarnings'] = ''

        if sessionKey != None:
            values['sessionkey'] = sessionKey

        if asyncDownload:
            values['asyncdownload'] = ''

        return self.apiRequest(values)

    def fileRevert(self, fileName, comment = ''):
        archiveName = self.query(titles = 'File:' + fileName, extraParams = {'prop':'imageinfo', 'iiprop':'archivename', 'iilimit':2})['query']['pages'].items()[0][1]['imageinfo'][1]['archivename']
        values = {'action':'filerevert', 'filename':fileName, 'archivename':archiveName, 'token':self.getEditToken()}

        if comment != '':
            values['comment'] = comment

        return self.apiRequest(values)

    def watch(self, title, unWatch = False):
        try:
            token = self.query(titles = 'Main Page', extraParams = {'prop':'info', 'intoken':'watch'})['query']['pages'].values()[0]['watchtoken']
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
            token = self.query(_list = 'recentchanges', extraParams = {'rctoken':'patrol', 'rclimit':'1'})['query']['recentchanges'][0]['patroltoken']
        except KeyError as keyError:
            if keyError.message == 'patroltoken':
                raise APIError, 'You may not patrol.'
            else:
                raise keyError

        return self.apiRequest({'action':'patrol', 'rcid':rcid, 'token':token})

    def _import(self):
        """See https://github.com/Krenair/PyMediaWikiClient/issues/1"""
        raise Exception, self._import.__doc__

    def userRights(self, user, add = [], remove = [], reason = None):
        try:
            token = self.query(_list = 'users', extraParams = {'ususers':user, 'ustoken':'userrights'})['query']['users'][0]['userrightstoken']
        except KeyError as keyError:
            if keyError.message == 'userrightstoken':
                raise APIError, 'You may not change user rights.'
            else:
                raise keyError

        headers = {'action':'userrights', 'user':user, 'add':add, 'remove':remove, 'token':token}

        if reason is not None:
            headers['reason'] = reason

        return self.apiRequest({}, headers)

class APIError(Exception):
    #Base class for exceptions in this module
    pass
