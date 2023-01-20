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

class StreamlinkItem:
    ch_list = None

    def __init__(self, id, title, url):
        self.id = id.strip()
        self.title = title.strip()
        self.url = url.strip()
        StreamlinkItem.ch_list[id] = self

class SourceStreamlink(SourceBase):
    channel_list = None

    @staticmethod
    def install():
        try:
            def func():
                import system
                import framework.common.util as CommonUtil
                commands = [['msg', u'잠시만 기다려주세요.']]
                if CommonUtil.is_docker():
                    commands.append(['apk', 'add', '--no-cache', '--virtual', '.build-deps', 'gcc', 'g++', 'make', 'libffi-dev', 'openssl-dev'])
                
                commands.append(['pip', 'install', '--upgrade', 'pip'])
                commands.append(['pip', 'install', '--upgrade', 'setuptools'])
                commands.append(['pip', 'install', 'streamlink'])
                if CommonUtil.is_docker():
                    commands.append(['apk', 'del', '.build-deps'])
                commands.append(['msg', u'설치가 완료되었습니다.'])
                system.SystemLogicCommand.start('설치', commands)
            t = threading.Thread(target=func, args=())
            t.setDaemon(True)
            t.start()
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())


    @staticmethod
    def is_installed():
        try:
            import streamlink
            return True
        except Exception as e: 
            pass
        return False


    @classmethod
    def get_channel_list(cls):
        try:
            tmp = ModelSetting.get('streamlink_list')
            StreamlinkItem.ch_list = {}
            ret = []
            for item in tmp.splitlines():
                if item.strip() == '':
                    continue
                tmp2 = item.split('|')
                if len(tmp2) != 3:
                    continue
                c = ModelChannel(cls.source_name, tmp2[0], tmp2[1], None, True)
                StreamlinkItem(tmp2[0], tmp2[1], tmp2[2])
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
            """
            import streamlink
            data = streamlink.streams(StreamlinkItem.ch_list[source_id].url)
            url = data[ModelSetting.get('streamlink_quality')].url
            """
            from streamlink import Streamlink
            s  = Streamlink()
            #logger.debug(StreamlinkItem.ch_list[source_id].url)
            data = s.streams(StreamlinkItem.ch_list[source_id].url)
            
            #logger.debug(len(data))
            

            try:
                stream = data[ModelSetting.get('streamlink_quality')]
                url = stream.url
            except Exception as e:
                #logger.error('Exception:%s', e)
                #logger.error(traceback.format_exc())
                if StreamlinkItem.ch_list[source_id].url.lower().find('youtube') != -1:
                    for k, t in data.items():
                        try:
                            url = t.url
                        except Exception as e:
                            #logger.error('Exception:%s', e)
                            #logger.error(traceback.format_exc())
                            pass
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
















