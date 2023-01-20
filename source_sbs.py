# -*- coding: utf-8 -*-
#########################################################
# python
import os
import sys
import logging
import traceback
import json
import re
import urllib
import requests
import threading

# third-party

# sjva 공용

# 패키지
from .plugin import logger, package_name
from .model import ModelSetting, ModelChannel
from .source_base import SourceBase

#########################################################

class SourceSBS(SourceBase):
    @classmethod
    def get_channel_list(cls):
        try:
            ret = []
            url_list = ['http://static.apis.sbs.co.kr/play-api/1.0/onair/channels', 'http://static.apis.sbs.co.kr/play-api/1.0/onair/virtual/channels']
            for url in url_list:
                data = requests.get(url).json()
                for item in data['list']:
                    title = item['channelname']
                    if item['channelid'] in ['S17', 'S18']:
                        title += ' (보는 라디오)'
                    c = ModelChannel(cls.source_name, item['channelid'], title, None, True if 'type' not in item or item['type'] == 'TV' else False)
                    c.current = item['title']
                    ret.append(c)
            return ret
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        return ret

    @classmethod
    def get_url(cls, source_id, quality, mode):
        try:
            url = cls.get_sbs_url(source_id)
            url = url.replace('playlist.m3u8', 'chunklist.m3u8')
            #2022-03-30
            return 'return_after_read', url
            #logger.debug(url)
            if mode == 'web_play':
                return 'return_after_read', url
            return 'redirect', url
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        return

    @classmethod
    def get_return_data(cls, source_id, url, mode):
        try:
            data = requests.get(url).text
            #logger.debug(data)
            tmp = url.split('chunklist')
            data = data.replace('media', tmp[0] + 'media')
            #logger.error(data)
            return data
            
            #return cls.change_redirect_data(data)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        return data


    @classmethod
    def get_sbs_url(cls, source_id):
        try:
            from support.base import default_headers
            prefix = '' if source_id != 'SBS' and int(source_id[1:]) < 21 else 'virtual/'
            #tmp = 'http://apis.sbs.co.kr/play-api/1.0/onair/%schannel/%s?v_type=2&platform=pcweb&protocol=hls&ssl=N&jwt-token=%s&rnd=462' % (prefix, source_id, '')
            tmp = f'https://apis.sbs.co.kr/play-api/1.0/onair/{prefix}channel/{source_id}?v_type=2&platform=pcweb&protocol=hls&ssl=N&rscuse=&jwt-token=&sbsmain='
            #logger.debug(tmp)

            proxies = None
            if ModelSetting.get_bool('sbs_use_proxy'):
                proxies = {
                    'http':ModelSetting.get('sbs_proxy_url'),
                    'https':ModelSetting.get('sbs_proxy_url'),
                }
            data = requests.get(tmp, headers=default_headers, proxies=proxies).json()
            from support.base import d
            #logger.debug(d(data))
            #logger.debug(tmp)
            url = data['onair']['source']['mediasource']['mediaurl']
            return url
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
