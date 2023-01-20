# -*- coding: utf-8 -*-
#########################################################
# python
import os
import sys
import logging
import re

# third-party

# sjva 공용
from framework.logger import get_logger
from framework import app, db, scheduler, path_app_root, SystemModelSetting, py_urllib

# 패키지
from .model import ModelSetting

# 로그
package_name = __name__.split('.')[0]
logger = get_logger(package_name)

#########################################################

class SourceBase:
    login_data = None

    @classmethod
    def __init__(cls, source_name, source_id, source_pw, arg):
        cls.source_name = source_name
        cls.prepare(source_id, source_pw, arg)

    @classmethod
    def prepare(cls, source_id, source_pw, arg):
        logger.debug('prepare')

    @classmethod
    def get_channel_list(cls):
        logger.debug('get_channel_list')
        
 
    @classmethod
    def get_url(cls, source_id, quality):
        logger.debug('get_url')
        
    @classmethod
    def get_return_data(cls, source_id, url):
        logger.debug('get_url')

    @classmethod
    def change_redirect_data(cls, data, proxy=None):
        try:
            #logger.debug(data)
            from system.model import ModelSetting as SystemModelSetting
            tmp = re.compile(r'http(.*?)$', re.MULTILINE).finditer(data)
            for m in tmp:
                u = m.group(0)
                u2 = '{ddns}/{package_name}/api/redirect?url={url}'.format(ddns=SystemModelSetting.get('ddns'), package_name=package_name, url=py_urllib.quote(u))
                if SystemModelSetting.get_bool('auth_use_apikey'):
                    u2 += '&apikey={apikey}'.format(apikey=SystemModelSetting.get('auth_apikey'))
                if proxy is not None:
                    u2 += '&proxy=%s' % proxy
                data = data.replace(u, u2)
            #logger.debug(data)
            return data
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            