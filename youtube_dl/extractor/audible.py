# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    get_element_by_class,
    urlencode_postdata,
)

#DEBUG
from pprint import pprint

class AudibleIE(InfoExtractor):
    IE_NAME = 'audible'
    _VALID_URL = r'https?://(?:.+?\.)?audible\.com/pd/(?:.+)/(?P<id>[^/?#&]+)'
    #_LOGIN_URL = 'https://www.amazon.com/ap/signin'
    #_LOGIN_URL_AMAZON = 'https://www.amazon.com/ap/signin?clientContext=133-5969337-7595328&openid.return_to=https%3A%2F%2Fwww.audible.com%2F&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=audible_shared_web_us&openid.mode=checkid_setup&marketPlaceId=AF2M0KC94RCEA&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&pageId=amzn_audible_bc_us&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0&openid.pape.max_auth_age=900&siteState=audibleid.userType%3Damzn%2Caudibleid.mode%3Did_res%2CclientContext%3D142-2025317-3674800%2CsourceUrl%3Dhttps%253A%252F%252Fwww.audible.com%252F%2Csignature%3DApPWGR9xVF5NXef335e4wDwKRR0j3D&pf_rd_p=39ae9f7a-40cd-4916-a788-abc2ff06af2e&pf_rd_r=8BQJ1ZN71C2NC4JRHKEE'
    _HOMEPAGE_URL = 'https://www.audible.com'
    _LOGIN_PREFIX_AMAZON = "amazon:"
    _LOGIN_URL_AMAZON = 'https://www.audible.com/sign-in/ref=private_to_ap?forcePublicSignIn=true&aui=1&rdPath=https%3A%2F%2Fwww.audible.com%2F'
    _LOGIN_PREFIX_AUDIBLE = "audible:"
    _LOGIN_URL_AUDIBLE = 'https://www.audible.com/sign-in/ref=ap_bc_to_private?forcePrivateSignIn=true&aui=1&rdPath=https%3A%2F%2Fwww.audible.com%2F'
    _TEST = {
        'url': 'https://www.audible.com/pd/Neil-Gaimans-How-the-Marquis-Got-His-Coat-Back-Audiobook/B01LZB4R8W',
        'md5': 'TODO: md5 sum of the first 10241 bytes of the video file (use --test)',
        'info_dict': {
            'id': 'B01LZB4R8W',
            'ext': 'mp4',
            'title': '???',
            'thumbnail': 're:^https?://.*\.jpg$',
            # TODO more properties, either as:
            # * A value
            # * MD5 checksum; start the string with md5:
            # * A regular expression; start the string with re:
            # * Any Python type (for example int or float)
        }
    }

    def _raise_captcha(self):
        raise ExtractorError(
            'Audible may ask you to solve a CAPTCHA. Login with browser, '
            'solve CAPTCHA, then export cookies and pass cookie file to '
            'youtube-dl with --cookies.', expected=True)

    def _login(self):
        username, password = self._get_login_info()
        if username is None:
            return

        if username.startswith(self._LOGIN_PREFIX_AMAZON):
            login_url = self._LOGIN_URL_AMAZON
            username = username[len(self._LOGIN_PREFIX_AMAZON):]
            #user_input = "email"
            #password_input = "password"
        elif username.startswith(self._LOGIN_PREFIX_AUDIBLE):
            login_url = self._LOGIN_URL_AUDIBLE
            username = username[len(self._LOGIN_PREFIX_AUDIBLE):]
        else:
            login_url = self._LOGIN_URL_AMAZON

        print "[!!!] " + username
        print "[!!!] " + login_url

        login_page = self._download_webpage(
            login_url, None, 'Downloading signin page')

        #pprint(login_page)

        login_form = self._hidden_inputs(login_page)

        login_form.update({
            'email': username,
            'password': password,
        })

        pprint(login_form)

        post_url = self._search_regex(
            r'<form[^>]+action=(["\'])(?P<url>.+?)\1', login_page,
            'post url', default=login_url, group='url')

        pprint(post_url)

        response, urlh = self._download_webpage_handle(
            post_url, None, 'Logging in', data=urlencode_postdata(login_form),
            headers={'Referer': login_url})

        pprint(urlh.geturl())

        #print response
        with open('response.html', 'w') as f:
        #with open('response.html', 'w', encoding='utf-8') as f:
            f.write(response.encode('utf-8'))


        captcha_url = self._search_regex(
            r'<img[^>]+src=(["\'])(?P<url>https://opfcaptcha-prod.s3.amazonaws.com/.+?)\1', response,
            'post url', default=None, group='url')


        pprint(captcha_url)

        captcha_urlh = self._request_webpage(
            captcha_url, None, 'retriving captcha image',
            headers={'Referer': login_url})


        pprint(captcha_urlh)


        #login_request = self._download_webpage(
        #    login_url, None,
        #    note='Logging in',
        #    data=urlencode_postdata(login_form),
        #    headers={
        #        'Referer': login_url,
        #    })

        #pprint(login_request)

        #if re.search(r'href=["\']/signout"', login_request) is not None:
        #    raise ExtractorError('Unable to log in')

    def _check_login_status(self):
        homepage = self._download_webpage(
            self._HOMEPAGE_URL, None,
            'Checking login status')

        logged_in_elm = get_element_by_class('ui-it-credit-balance', homepage)

        if logged_in_elm is None:
            raise ExtractorError(
                'It is currently not possible to automate the login process for '
                'Audible. You must login via a browser, then export your cookies '
                'and pass the cookie file to youtube-dl with --cookies.',
                expected=True)

    def _real_initialize(self):
        #self._login()
        self._check_login_status()

    def _real_extract(self, url):
        book_id = self._match_id(url)
        # we don't actually care about the url,
        # we just need it to get the book_id
        print "[!!!] " + book_id
        webpage = self._download_webpage(url, book_id)

        title = self._og_search_title(webpage)


        cloud_player_url = 'https://www.audible.com/cloudplayer?asin=' + book_id
        cloud_player_page = self._download_webpage(
            cloud_player_url, book_id, 'Retrieving token')
        cloud_player_form = self._hidden_inputs(cloud_player_page)
        pprint(cloud_player_form)

        token = cloud_player_form.get('token')
        if token is None:
            raise ExtractorError("Could not find token")
        print "[!!!] " + token

        #metadata = self._download_webpage(
        metadata = self._download_json(
            'https://www.audible.com/contentlicenseajax', book_id,
            data=urlencode_postdata({
                'asin': book_id,
                'token': token,
                'key': 'AudibleCloudPlayer',
                'action': 'getUrl'
            }))
        pprint(metadata)

        f4m_url = metadata.get('hdscontentLicenseUrl')
        m3u8_url = metadata.get('hlscontentLicenseUrl')

        #_extract_akamai_formats
        formats = []
        if m3u8_url:
            formats.extend(self._extract_m3u8_formats(
                m3u8_url, book_id, 'mp4', 'm3u8_native',
                m3u8_id='hls', fatal=False))
        #if f4m_url:
        #    formats.extend(self._extract_akamai_formats(
        #        f4m_url, book_id))
        #if m3u8_url:
        #    formats.extend(self._extract_akamai_formats(
        #        m3u8_url, book_id))
        self._sort_formats(formats)

        #with open('webpage.html', 'w') as f:
        #    f.write(webpage.encode('utf-8'))

        return {
            'id': book_id,
            'title': title,
            'formats': formats,
            # TODO more properties (see youtube_dl/extractor/common.py)
        }

class AudibleLibraryIE(InfoExtractor):
    IE_NAME = 'audible:library'