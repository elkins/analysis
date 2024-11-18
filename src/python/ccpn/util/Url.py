"""Utilities for Url handling
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Morgan Hayward, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Daniel Thompson",
               "Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-11-18 13:26:24 +0000 (Mon, November 18, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import os
import ssl
import certifi
import urllib
from urllib.request import getproxies
import urllib3
from ccpn.util.UserPreferences import UserPreferences, USEPROXY, USEPROXYPASSWORD, PROXYADDRESS, \
    PROXYPORT, PROXYUSERNAME, PROXYPASSWORD, VERIFYSSL
from ccpn.util.Logging import getLogger


BAD_DOWNLOAD = 'Exception: '


def _getProxyIn(proxyDict):
    """Get the first occurrence of a proxy type in the supplied dict.
    """
    # define a list of proxy identifiers
    proxyCheckList = ['HTTPS_PROXY', 'https', 'HTTP_PROXY', 'http']
    for pCheck in proxyCheckList:
        if _proxyUrl := proxyDict.get(pCheck, None):
            return _proxyUrl


def _userPrefs(proxySettings):
    _userPreferences = UserPreferences(readPreferences=True)
    if _userPreferences.proxyDefined:
        proxyNames = ['useProxy', 'proxyAddress', 'proxyPort', 'useProxyPassword',
                      'proxyUsername', 'proxyPassword', 'verifySSL']
        proxySettings = {name: _userPreferences._getPreferencesParameter(name) for name in proxyNames}
    return proxySettings


def fetchHttpResponse(method, url, data=None, headers=None, proxySettings=None):
    """Generate http request, and return the response
    """
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    # Create the options list for creating an HTTP connection
    options = {
        'cert_reqs': 'CERT_REQUIRED',
        'ca_certs' : certifi.where(),
        'retries'  : urllib3.Retry(1, redirect=False)
        }

    if proxySettings:
        verifySSL = proxySettings.get(VERIFYSSL, True)
        options['cert_reqs'] = ssl.CERT_REQUIRED if verifySSL else ssl.CERT_NONE
        if not verifySSL:
            urllib3.disable_warnings()
            getLogger().warning('SSL certificates validity check skipped.')
        if proxySettings.get(USEPROXY):
            # Use the user settings if set
            useProxyPassword = proxySettings.get(USEPROXYPASSWORD)
            proxyAddress = proxySettings.get(PROXYADDRESS)
            proxyPort = proxySettings.get(PROXYPORT)
            proxyUsername = proxySettings.get(PROXYUSERNAME)
            proxyPassword = proxySettings.get(PROXYPASSWORD)
            if useProxyPassword:
                # grab decode from the userPreferences
                _userPreferences = UserPreferences(readPreferences=False)
                options.update({'headers': urllib3.make_headers(proxy_basic_auth='%s:%s' %
                                                                                 (proxyUsername,
                                                                                  _userPreferences.decodeValue(
                                                                                          proxyPassword)))})
            proxyUrl = f"{proxyAddress}:{proxyPort}" if proxyAddress else None
        else:
            # read the environment/system proxies if exist
            proxyUrl = _getProxyIn(os.environ) or _getProxyIn(urllib.request.getproxies())
    else:
        # read the environment/system proxies if exist
        proxyUrl = _getProxyIn(os.environ) or _getProxyIn(urllib.request.getproxies())

    # ED: issues - @"HTTPProxyAuthenticated" key on system?. If it exists, the value is a boolean (NSNumber) indicating whether or not the proxy is authentified,
    # get the username if the proxy is authenticated: check @"HTTPProxyUsername"

    # proxy may still not be defined
    http = urllib3.ProxyManager(proxyUrl, **options) if proxyUrl else urllib3.PoolManager(**options)
    try:
        # Make the HTTP request - does not like a context-manager here
        if response := http.request(method, url, fields=data, headers=headers):
            return response.data
    except Exception as es:
        getLogger().warning(f"Error getting connection - {es}")
    finally:
        http.clear()


def fetchUrl(url, data=None, headers=None, timeout=5, proxySettings=None, decodeResponse=True):
    """Fetch url request from the server
    """
    import logging
    from ccpn.core.lib.ContextManagers import Timeout as timer
    from ccpn.util.Common import isWindowsOS


    urllib3_logger = logging.getLogger('urllib3')
    urllib3_logger.setLevel(logging.CRITICAL)
    timeoutMessage = 'Could not connect to server. Check connection'
    if isWindowsOS():
        # Windows does not have signal.SIGALRM - temporary fix
        proxySettings = proxySettings or _userPrefs(proxySettings)
        result = fetchHttpResponse('POST', url, data=data, headers=headers,
                                   proxySettings=proxySettings)
    else:
        # use the timeout limited call - still required?
        with timer(seconds=timeout or 5, timeoutMessage=timeoutMessage):
            proxySettings = proxySettings or _userPrefs(proxySettings)
            result = fetchHttpResponse('POST', url, data=data, headers=headers,
                                       proxySettings=proxySettings)
    if result:
        return result.decode('utf-8') if decodeResponse else result


def uploadFile(url, fileName, data=None):
    import os

    if not data:
        data = {}

    with open(fileName, 'rb') as fp:
        fileData = fp.read()

    data['fileName'] = os.path.basename(fileName)
    data['fileData'] = fileData

    try:
        return fetchUrl(url, data)
    except:
        return None


def checkInternetConnection():
    """Check whether an internet conection is available by testing the CCPN weblink
    """
    from ccpn.framework.PathsAndUrls import ccpnUrl

    try:
        fetchUrl('/'.join([ccpnUrl, 'cgi-bin/checkInternet']))
        return True

    except Exception as es:
        getLogger().exception(es)
        return False
