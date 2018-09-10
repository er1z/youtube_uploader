from itertools import combinations

import wx
import wx.html2
from google_auth_oauthlib.flow import InstalledAppFlow
from urllib.parse import urlparse, parse_qs
from googleapiclient.discovery import build

CLIENT_SECRETS_FILE = 'client_secret.json'

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

class OAuth(wx.Dialog):
    def __init__(self, *args, **kwds):
        wx.Dialog.__init__(self, *args, **kwds)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.browser = wx.html2.WebView.New(self)
        self.browser.LoadURL(
            self.get_auth_url()
        )

        self.browser.Bind(wx.html2.EVT_WEBVIEW_ERROR, self.redirect_callback)

        sizer.Add(self.browser, 1, wx.EXPAND, 10)
        self.SetSizer(sizer)
        self.SetSize((700, 700))
        self.result = None

        self.Bind(wx.EVT_CLOSE, self.on_close)

    def get_auth_url(self):
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
        flow.redirect_uri = 'http://localhost'
        #credentials = flow.run_console()
        return flow.authorization_url()[0]
        #return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

    def on_close(self, evt):
        self.EndModal(False)

    def redirect_callback(self, evt):
        redirect_url = evt.GetURL()
        components = urlparse(redirect_url)
        query = components.query
        query_components = parse_qs(query)
        # todo check if code is present, if not — fail
        code = query_components['code'][0]

        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES, redirect_uri='http://localhost')

        flow.fetch_token(code=code)
        self.result = build(API_SERVICE_NAME, API_VERSION, credentials=flow.credentials)

        self.EndModal(True)