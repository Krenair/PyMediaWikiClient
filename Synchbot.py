# This script creates pages across most Wikimedia wikis.
# I might add some preferences (language, skin, signature) support once https://gerrit.wikimedia.org/r/#/c/5126/ has been deployed.

username = 'Krenair'
password = 'example'
title = 'User:Krenair/common.js'
text = "mw.loader.load('//meta.wikimedia.org/w/index.php?title=User:Krenair/global.js&action=raw&ctype=text/javascript');"
minor = True
summary = 'Global JavaScript.'
excludeWikis = ['enwiki', 'mediawikiwiki', 'metawiki']

# Do not modify anything below here unless you know what you are doing.

from cookielib import CookieJar
from MediaWikiClient import MediaWikiClient
import time, sys

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

    print wiki['dbname'] + ":", mwc.apiRequest({'action':'edit', 'token':mwc.getEditToken(), 'title':title, 'text':text, 'summary':summary, 'minor':minor})
    try:
        time.sleep(5)
    except KeyboardInterrupt:
        print ''
        sys.exit(0) #Die non-violently if interrupted while not doing anything.
