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

class NavertvItem:
    ch_list = None

    def __init__(self, id, title, url, quality):
        self.id = id.strip()
        self.title = title.strip()
        self.url = url.strip()
        self.quality = quality.strip()
        NavertvItem.ch_list[id] = self

class SourceNavertv(SourceBase):
    @classmethod
    def get_channel_list(cls):
        try:
            tmp = ModelSetting.get('navertv_list')
            NavertvItem.ch_list = {}
            ret = []
            for item in tmp.splitlines():
                if item.strip() == '':
                    continue
                tmp2 = item.split('|')
                if len(tmp2) < 3:
                    continue
                c = ModelChannel(cls.source_name, tmp2[0], tmp2[1], None, True)
                quality = '1080' if len(tmp2) == 3 else tmp2[3]
                NavertvItem(tmp2[0], tmp2[1], tmp2[2], quality)
                c.current = ''
                ret.append(c)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        return ret

    @classmethod
    def get_url(cls, source_id, quality, mode):
        try:
            #logger.debug('source_id:%s, quality:%s, mode:%s', source_id, quality, mode)
            target_url = NavertvItem.ch_list[source_id].url
            url = cls.get_naver_url(target_url, NavertvItem.ch_list[source_id].quality)
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
            return cls.change_redirect_data(data)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        return data


    @classmethod
    def get_naver_url(cls, target_url, quality):
        try:
            from support.base import default_headers
            if target_url.startswith('SPORTS_'):
                target_ch = target_url.split('_')[1]
                if not target_ch.startswith('ad') and not target_ch.startswith('ch'):
                    target_ch = 'ch' + target_ch
                qua = '5000'
                tmp = {'480':'800', '720':'2000', '1080':'5000'}
                qua = tmp[quality] if quality in tmp else qua
                tmp = 'https://apis.naver.com/pcLive/livePlatform/sUrl?ch=%s&q=%s&p=hls&cc=KR&env=pc' % (target_ch, qua)
                url = requests.get(tmp, headers=headers).json()['secUrl']

                #https://proxy-gateway.sports.naver.com/livecloud/lives/3278079/playback?countryCode=KR&devt=HTML5_PC&timeMachine=true&p2p=true&includeThumbnail=true&pollingStatus=true
            else:
                #logger.debug(target_url)
                text = requests.get(target_url, headers=default_headers).text
                match = re.search(r'liveId: \'(?P<liveid>\d+)\'', text)
                #logger.debug(match)
                if match:
                    liveid = match.group('liveid')
                    #https://api.tv.naver.com/api/open/live/v2/player/playback?liveId=3077128&countryCode=KR&timeMachine=true
                    json_url = f"https://api.tv.naver.com/api/open/live/v2/player/playback?liveId={liveid}&countryCode=KR&timeMachine=true"
                    data = requests.get(json_url, headers=default_headers).json()

                    url = data['media'][0]['path']
            return url
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
    
    
        #