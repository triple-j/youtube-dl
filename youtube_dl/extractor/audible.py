# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    ExtractorError,
    extract_attributes,
    get_element_by_class,
    urlencode_postdata,
)

#DEBUG
from pprint import pprint

class AudibleIE(InfoExtractor):
    IE_NAME = 'audible'
    _VALID_URL = r'https?://(?:.+?\.)?audible\.com/pd/(?:.+)/(?P<id>[^/?#&]+)'
    _HOMEPAGE_URL = 'https://www.audible.com'
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

    @staticmethod
    def _get_label_text(class_name, html, prefix=None):
        label_text = None

        label_html = get_element_by_class(class_name, html)
        if label_html:
            label_text = re.sub(r'\s+', ' ', clean_html(label_html))
            if prefix and label_text.startswith(prefix):
                label_text = label_text[len(prefix):].strip()

        return label_text

    def _check_login_status(self, html=None):
        if not html:
            html = self._download_webpage(
                self._HOMEPAGE_URL, None,
                'Checking login status')

        logged_in_elm = get_element_by_class('ui-it-credit-balance', html)

        if logged_in_elm is None:
            raise ExtractorError(
                'It is currently not possible to automate the login process for '
                'Audible. You must login via a browser, then export your cookies '
                'and pass the cookie file to youtube-dl with --cookies.',
                expected=True)

    def _real_initialize(self):
        self._check_login_status()

    def _real_extract(self, url):
        book_id = self._match_id(url)
        webpage = self._download_webpage(url, book_id)

        '''
        info from web page

        ~title~
        author(s)       -> creator / ~artist: Artist(s) of the track.~ / album_artist
        narrator(s)     -> artist: Artist(s) of the track.
        format/type     -> ~categories~ / ~tags~ / album_type
        Release date    -> release_date: The date (YYYYMMDD) when the video was released. / release_year: Year (YYYY) when the album was released.
        Language
        Publisher       -> uploader
        breadcrumbs     -> categories / ~tags~ / genre
        ~thumbnail~
        rating          -> average_rating
        series          -> series
        book in series  -> episode_number / track_number
        Publisher's Summary -> description
        Critic Reviews      -> description

        What members say    -> comments

        '''

        title = self._og_search_title(webpage)

        thumbnails = []

        og_thumbnail = self._og_search_thumbnail(webpage)
        if og_thumbnail:
            thumbnails.append({
                'url': og_thumbnail,
                'preference': 210
            })

        thumb_element = self._search_regex(
            r'(<img[^>]+alt=["\'][^\'"]*\bcover art\b[^>]*>)', webpage,
            'thumbnail element', default=None)
        if thumb_element:
            lg_thumbnail_attrs = extract_attributes(thumb_element)
            if lg_thumbnail_attrs.get('src'):
                thumbnails.append({
                    'url': lg_thumbnail_attrs.get('src'),
                    'preference': 500
                })

        authors = self._get_label_text('authorLabel', webpage, prefix='By:')
        narrators = self._get_label_text('narratorLabel', webpage, prefix='Narrated by:')
        performance_type = self._get_label_text('format', webpage)
        publisher = self._get_label_text('publisherLabel', webpage, prefix='Publisher:')

        release_date_yyyymmdd = None
        release_year_yyyy = None
        release_date = self._get_label_text('releaseDateLabel', webpage, prefix='Release date:')
        pprint(release_date)
        if release_date:
            mobj = re.search(r'(?P<mm>\d{2})-(?P<dd>\d{2})-(?P<yy>\d{2})', release_date)
            if mobj:
                if int(mobj.group('yy')) >= 80:
                    # FYI this will break in the year 2080
                    release_year_yyyy = "19" + mobj.group('yy')
                else:
                    release_year_yyyy = "20" + mobj.group('yy')
                release_date_yyyymmdd = release_year_yyyy + mobj.group('mm') + mobj.group('dd')

        # Everything below this line requires a login --------------------------

        # TODO: run `_check_login_status` here instead of in `_real_initialize` (reduce page downloads)
        # TODO: gracefully fail when a user doesn't have access to a book

        cloud_player_url = 'https://www.audible.com/cloudplayer?asin=' + book_id
        cloud_player_page = self._download_webpage(
            cloud_player_url, book_id, 'Retrieving token')
        cloud_player_form = self._hidden_inputs(cloud_player_page)

        token = cloud_player_form.get('token')
        if token is None:
            raise ExtractorError("Could not find token")

        metadata = self._download_json(
            'https://www.audible.com/contentlicenseajax', book_id,
            data=urlencode_postdata({
                'asin': book_id,
                'token': token,
                'key': 'AudibleCloudPlayer',
                'action': 'getUrl'
            }))

        #f4m_url = metadata.get('hdscontentLicenseUrl')
        m3u8_url = metadata.get('hlscontentLicenseUrl')
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

        duration = metadata.get('runTime')

        chapters = []
        for md_chapter in metadata.get('cloudPlayerChapters', []):
            ch_start_time = md_chapter.get('chapterStartPosition')
            ch_end_time = md_chapter.get('chapterEndPosition')
            ch_title = md_chapter.get('chapterTitle')

            if ch_start_time is None or ch_end_time is None:
                self.report_warning('Missing chapter information')
                chapters = []
                break

            chapter = {
                'start_time': float(ch_start_time) / 1000,
                'end_time': float(ch_end_time) / 1000
            }

            if title:
                chapter['title'] = ch_title

            chapters.append(chapter)

        return {
            'id': book_id,
            'title': title,
            'formats': formats,
            'duration': duration,
            'chapters': chapters if len(chapters) > 0 else None,
            'thumbnails': thumbnails if len(thumbnails) > 0 else None,
            'creator': authors,
            'album_artist': authors,
            'artist': narrators,
            'album_type': performance_type,
            'uploader': publisher,
            'release_date': release_date_yyyymmdd,
            'release_year': release_year_yyyy,
            # TODO more properties (see youtube_dl/extractor/common.py)
        }

class AudibleLibraryIE(InfoExtractor):
    IE_NAME = 'audible:library'