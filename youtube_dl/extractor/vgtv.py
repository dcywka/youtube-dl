# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from .xstream import XstreamIE
from ..utils import (
    ExtractorError,
    float_or_none,
)


class VGTVIE(XstreamIE):
    IE_DESC = 'VGTV, BTTV, FTV, Aftenposten and Aftonbladet'

    _HOST_TO_APPNAME = {
        'vgtv.no': 'vgtv',
        'bt.no/tv': 'bttv',
        'aftenbladet.no/tv': 'satv',
        'fvn.no/fvntv': 'fvntv',
        'aftenposten.no/webtv': 'aptv',
    }

    _APP_NAME_TO_VENDOR = {
        'vgtv': 'vgtv',
        'bttv': 'bt',
        'satv': 'sa',
        'fvntv': 'fvn',
        'aptv': 'ap',
    }

    _VALID_URL = r'''(?x)
                    (?:https?://(?:www\.)?
                    (?P<host>
                        %s
                    )
                    /
                    (?:
                        \#!/(?:video|live)/|
                        embed?.*id=
                    )|
                    (?P<appname>
                        %s
                    ):)
                    (?P<id>\d+)
                    ''' % ('|'.join(_HOST_TO_APPNAME.keys()), '|'.join(_APP_NAME_TO_VENDOR.keys()))

    _TESTS = [
        {
            # streamType: vod
            'url': 'http://www.vgtv.no/#!/video/84196/hevnen-er-soet-episode-10-abu',
            'md5': 'b8be7a234cebb840c0d512c78013e02f',
            'info_dict': {
                'id': '84196',
                'ext': 'mp4',
                'title': 'Hevnen er søt: Episode 10 - Abu',
                'description': 'md5:e25e4badb5f544b04341e14abdc72234',
                'thumbnail': 're:^https?://.*\.jpg',
                'duration': 648.000,
                'timestamp': 1404626400,
                'upload_date': '20140706',
                'view_count': int,
            },
        },
        {
            # streamType: wasLive
            'url': 'http://www.vgtv.no/#!/live/100764/opptak-vgtv-foelger-em-kvalifiseringen',
            'info_dict': {
                'id': '100764',
                'ext': 'flv',
                'title': 'OPPTAK: VGTV følger EM-kvalifiseringen',
                'description': 'md5:3772d9c0dc2dff92a886b60039a7d4d3',
                'thumbnail': 're:^https?://.*\.jpg',
                'duration': 9103.0,
                'timestamp': 1410113864,
                'upload_date': '20140907',
                'view_count': int,
            },
            'params': {
                # m3u8 download
                'skip_download': True,
            },
            'skip': 'Video is no longer available',
        },
        {
            # streamType: wasLive
            'url': 'http://www.vgtv.no/#!/live/113063/direkte-v75-fra-solvalla',
            'md5': '458f4841239dab414343b50e5af8869c',
            'info_dict': {
                'id': '113063',
                'ext': 'flv',
                'title': 'V75 fra Solvalla 30.05.15',
                'description': 'md5:b3743425765355855f88e096acc93231',
                'thumbnail': 're:^https?://.*\.jpg',
                'duration': 25966,
                'timestamp': 1432975582,
                'upload_date': '20150530',
                'view_count': int,
            },
        },
        {
            'url': 'http://www.aftenposten.no/webtv/#!/video/21039/trailer-sweatshop-i-can-t-take-any-more',
            'md5': 'fd828cd29774a729bf4d4425fe192972',
            'info_dict': {
                'id': '21039',
                'ext': 'mov',
                'title': 'TRAILER: «SWEATSHOP» - I can´t take any more',
                'description': 'md5:21891f2b0dd7ec2f78d84a50e54f8238',
                'duration': 66,
                'timestamp': 1417002452,
                'upload_date': '20141126',
                'view_count': int,
            }
        },
        {
            'url': 'http://www.bt.no/tv/#!/video/100250/norling-dette-er-forskjellen-paa-1-divisjon-og-eliteserien',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')
        host = mobj.group('host')
        appname = self._HOST_TO_APPNAME[host] if host else mobj.group('appname')
        vendor = self._APP_NAME_TO_VENDOR[appname]

        data = self._download_json(
            'http://svp.vg.no/svp/api/v1/%s/assets/%s?appName=%s-website'
            % (vendor, video_id, appname),
            video_id, 'Downloading media JSON')

        if data.get('status') == 'inactive':
            raise ExtractorError(
                'Video %s is no longer available' % video_id, expected=True)

        info = {
            'formats': [],
        }
        if len(video_id) == 5:
            if appname == 'bttv':
                info = self._extract_video_info('btno', video_id)
            elif appname == 'aptv':
                info = self._extract_video_info('ap', video_id)

        streams = data['streamUrls']
        stream_type = data.get('streamType')

        formats = []

        hls_url = streams.get('hls')
        if hls_url:
            m3u8_formats = self._extract_m3u8_formats(
                hls_url, video_id, 'mp4', m3u8_id='hls', fatal=False)
            if m3u8_formats:
                formats.extend(m3u8_formats)

        hds_url = streams.get('hds')
        if hds_url:
            hdcore_sign = 'hdcore=3.7.0'
            f4m_formats = self._extract_f4m_formats(
                hds_url + '?%s' % hdcore_sign, video_id, f4m_id='hds', fatal=False)
            if f4m_formats:
                for entry in f4m_formats:
                    # URLs without the extra param induce an 404 error
                    entry.update({'extra_param_to_segment_url': hdcore_sign})
                    formats.append(entry)

        mp4_urls = streams.get('pseudostreaming') or []
        mp4_url = streams.get('mp4')
        if mp4_url:
            mp4_urls.append(mp4_url)
        for mp4_url in mp4_urls:
            format_info = {
                'url': mp4_url,
            }
            mobj = re.search('(\d+)_(\d+)_(\d+)', mp4_url)
            if mobj:
                tbr = int(mobj.group(3))
                format_info.update({
                    'width': int(mobj.group(1)),
                    'height': int(mobj.group(2)),
                    'tbr': tbr,
                    'format_id': 'mp4-%s' % tbr,
                })
            formats.append(format_info)

        info['formats'].extend(formats)

        self._sort_formats(info['formats'])

        info.update({
            'id': video_id,
            'title': self._live_title(data['title']) if stream_type == 'live' else data['title'],
            'description': data['description'],
            'thumbnail': data['images']['main'] + '?t[]=900x506q80',
            'timestamp': data['published'],
            'duration': float_or_none(data['duration'], 1000),
            'view_count': data['displays'],
            'is_live': True if stream_type == 'live' else False,
        })
        return info


class BTArticleIE(InfoExtractor):
    IE_NAME = 'bt:article'
    IE_DESC = 'Bergens Tidende Articles'
    _VALID_URL = 'http://(?:www\.)?bt\.no/(?:[^/]+/)+(?P<id>[^/]+)-\d+\.html'
    _TEST = {
        'url': 'http://www.bt.no/nyheter/lokalt/Kjemper-for-internatet-1788214.html',
        'md5': '2acbe8ad129b3469d5ae51b1158878df',
        'info_dict': {
            'id': '23199',
            'ext': 'mp4',
            'title': 'Alrekstad internat',
            'description': 'md5:dc81a9056c874fedb62fc48a300dac58',
            'thumbnail': 're:^https?://.*\.jpg',
            'duration': 191,
            'timestamp': 1289991323,
            'upload_date': '20101117',
            'view_count': int,
        },
    }

    def _real_extract(self, url):
        webpage = self._download_webpage(url, self._match_id(url))
        video_id = self._search_regex(
            r'<video[^>]+data-id="(\d+)"', webpage, 'video id')
        return self.url_result('bttv:%s' % video_id, 'VGTV')


class BTVestlendingenIE(InfoExtractor):
    IE_NAME = 'bt:vestlendingen'
    IE_DESC = 'Bergens Tidende - Vestlendingen'
    _VALID_URL = 'http://(?:www\.)?bt\.no/spesial/vestlendingen/#!/(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.bt.no/spesial/vestlendingen/#!/86588',
        'md5': 'd7d17e3337dc80de6d3a540aefbe441b',
        'info_dict': {
            'id': '86588',
            'ext': 'mov',
            'title': 'Otto Wollertsen',
            'description': 'Vestlendingen Otto Fredrik Wollertsen',
            'timestamp': 1430473209,
            'upload_date': '20150501',
        },
        'skip': '404 Error',
    }, {
        'url': 'http://www.bt.no/spesial/vestlendingen/#!/86255',
        'md5': 'a2893f8632e96389f4bdf36aa9463ceb',
        'info_dict': {
            'id': '86255',
            'ext': 'mov',
            'title': 'Du må tåle å fryse og være sulten',
            'description': 'md5:b8046f4d022d5830ddab04865791d063',
            'upload_date': '20150321',
            'timestamp': 1426942023,
        },
    }]

    def _real_extract(self, url):
        return self.url_result('bttv:%s' % self._match_id(url), 'VGTV')
