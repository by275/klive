# -*- coding: utf-8 -*-
#########################################################
# python
import os, time
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
from support.base import d, default_headers

#########################################################

class SourceMBC(SourceBase):
    code = {
        'MBC' : '0',
        'P_everyone' : '2',
        'P_drama' : '1',
        'P_music' : '3',
        'P_on' : '6',
        'P_allthekpop' : '4',
        'FM' : 'sfm',
        'FM4U' : 'mfm',
        'ALLTHAT' : 'chm',
    }

    @classmethod
    def get_channel_list(cls):
        try:
            ret = []
            url = 'https://control.imbc.com/Schedule/PCONAIR'
            data = requests.get(url, headers=default_headers).json()
            for cate in ['TVList', 'RadioList']:
                for item in data[cate]:
                    if item['ScheduleCode'] not in cls.code:
                        continue
                    c = ModelChannel(cls.source_name, cls.code[item['ScheduleCode']], item['TypeTitle'], None, True if cate=='TVList' else False)
                    c.current = item['Title']
                    ret.append(c)
            return ret
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        return ret

    @classmethod
    def get_url(cls, source_id, quality, mode):
        try:
            headers = {
                'Host': 'mediaapi.imbc.com',
                'Origin': 'https://onair.imbc.com',
                'Referer': 'https://onair.imbc.com/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36',
            }
            if len(source_id) == 3:
                url = f'https://sminiplay.imbc.com/aacplay.ashx?channel={source_id}&protocol=M3U8&agent=webapp'
                #logger.debug(url)
                data = requests.get(url).text
                data = data.replace('playlist', 'chunklist')
                #logger.debug(data)
                return 'redirect', data
            elif source_id != '0':
                url = f'https://mediaapi.imbc.com/Player/OnAirPlusURLUtil?ch={source_id}&type=PC&t={int(time.time())}'
            else:
                url = f'https://mediaapi.imbc.com/Player/OnAirURLUtil?type=PC&t={int(time.time())}'
            data = requests.get(url, headers=headers, verify=False).json()
            url = data['MediaInfo']['MediaURL'].replace('playlist', 'chunklist')
            return 'return_after_read', url

        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        return

    @classmethod
    def get_return_data(cls, source_id, url, mode):
        try:
            data = requests.get(url, headers=default_headers).text
            #data = cls.change_redirect_data(data)
            tmp = url.split('chunklist')
            data = data.replace('media', tmp[0] + 'media')
            return data
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        return data
