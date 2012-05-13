# This script creates pages and changes preferences across most Wikimedia wikis.
# The preferences bit won't work until https://gerrit.wikimedia.org/r/#/c/5126/ has been deployed.

username = 'Krenair'
password = 'example'

edit = True
#title = 'User:Krenair/common.js'
#text = "mw.loader.load('//meta.wikimedia.org/w/index.php?title=User:Krenair/global.js&action=raw&ctype=text/javascript');"
title = 'User:Krenair'
text = '{{#ifeq:{{CONTENTLANGUAGE}}|en|{{#babel:en-N}}|{{#babel:{{CONTENTLANGUAGE}}-0}}}}[[File:Redirectltr.png|#REDIRECT|link=]]<span class="redirectText" id="softredirect">[[:w:en:User:Krenair|See my user page on the English Wikipedia]]</span><br /><span style="font-size:85%; padding-left:52px;">This page is a [[w:en:Wikipedia:Soft redirect|soft redirect]].</span>'
minor = True
summary = 'Global user page.'
excludeWikis = ['enwiki', 'mediawikiwiki']

preferences = False
skin = 'vector'
#language = 'en'
language = None
signature = None
#signature = '[[User:Krenair|<span style="color: orange; font-weight: bold;">Krenair</span>]] <sup>([[User talk:Krenair|talk]] &bull; [[Special:Contributions/Krenair|contribs]])</sup>'

# Do not modify anything below here unless you know what you are doing.

import sys

if not edit and not preferences:
    print 'You must set edit or preferences to True.'
    sys.exit(0)

from cookielib import CookieJar
from MediaWikiClient import MediaWikiClient
import time

metawikiclient = MediaWikiClient('http://meta.wikimedia.org/w/api.php')

def getAllNormalWikis():
    wikis = []
    for id, langorspecial in metawikiclient.apiRequest({'action':'sitematrix'})['sitematrix'].items():
        if id == 'count':
            continue
        elif id == 'specials':
            pass #Most special wikis are chapters or test wikis, so we add the relevant ones manually
            #for site in langorspecial:
                #wikis.append(site)
        elif id != 'specials':
            for site in langorspecial['site']:
                wikis.append(site)
    wikis.append({'url':'http://beta.wikiversity.org', 'code':'betawikiversity', 'dbname':'betawikiversity'})
    wikis.append({'url':'http://commons.wikimedia.org', 'code':'commons', 'dbname':'commonswiki'})
    wikis.append({'url':'http://incubator.wikimedia.org', 'code':'incubator', 'dbname':'incubatorwiki'})
    wikis.append({'url':'http://www.mediawiki.org', 'code':'mediawiki', 'dbname':'mediawikiwiki'})
    wikis.append({'url':'http://outreach.wikimedia.org', 'code':'outreach', 'dbname':'outreachwiki'})
    wikis.append({'url':'http://wikisource.org', 'code':'sources', 'dbname':'sourceswiki'})
    wikis.append({'url':'http://species.wikimedia.org', 'code':'species', 'dbname':'specieswiki'})
    wikis.append({'url':'http://strategy.wikimedia.org', 'code':'strategy', 'dbname':'strategywiki'})
    return wikis

wikis = getAllNormalWikis()
CJ = CookieJar()

accountMergedWikis = []

for mergedAccount in metawikiclient.apiRequest({'action':'query', 'meta':'globaluserinfo', 'guiuser':username, 'guiprop':'merged'})['query']['globaluserinfo']['merged']:
    accountMergedWikis.append(mergedAccount['wiki'])

#wikis = [{'url':'http://localhost/MediaWiki/TestWikis/DevTest/api.php', 'dbname':'localtest'}]
#accountMergedWikis = ['localtest']

for wiki in wikis:
    if wiki['dbname'] in excludeWikis: #If the wiki has been specified as excluded, skip.
        print wiki['dbname'] + ": Skipped because of exclusion."
        continue
    elif 'closed' in wiki or 'private' in wiki: #If the wiki is closed or private, skip.
        continue
    elif wiki['dbname'] not in accountMergedWikis: #If the account is not merged on this wiki, skip.
        print wiki['dbname'] + ": Skipped because the account is not merged on this wiki."
        continue

    mwc = MediaWikiClient(wiki['url'] + '/w/api.php', userAgent = "Krenair's Synchbot", cookieJar = CJ)

    if mwc.userInfo['name'] != username: #If we're already logged in, for example when our cookie has been given by en.wikipedia.org but is valid for *.wikipedia.org, don't log in again.
        mwc.login(username, password)

    if edit:
        print wiki['dbname'] + ":", mwc.apiRequest({'action':'edit', 'token':mwc.getEditToken(), 'title':title, 'text':text, 'summary':summary, 'minor':minor})

    if preferences:
        preferencestoken = mwc.getEditToken()
        if signature: #Skin should always be handled separately because it's almost always going to contain pipe characters.
            print wiki['dbname'] + ':', mwc.apiRequest({'action':'options', 'token':preferencestoken, 'optionname':'signature', 'optionvalue':signature})

        if skin and language: #If we're changing skin and language, do it in one request.
            print wiki['dbname'] + ':', mwc.apiRequest({'action':'options', 'token':preferencestoken, 'change':'language=' + language + '|skin=' + skin})
        elif skin: #Otherwise, handle them separately.
            print wiki['dbname'] + ':', mwc.apiRequest({'action':'options', 'token':preferencestoken, 'optionname':'skin', 'optionvalue':skin})
        elif language:
            print wiki['dbname'] + ':', mwc.apiRequest({'action':'options', 'token':preferencestoken, 'optionname':'language', 'optionvalue':language})

    try:
        time.sleep(5)
    except KeyboardInterrupt:
        print ''
        sys.exit(0) #Die non-violently if interrupted while not doing anything.
