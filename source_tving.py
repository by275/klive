import os, sys, traceback, requests, re
from framework import SystemModelSetting

from .plugin import logger, package_name
from .model import ModelSetting, ModelChannel
from .source_base import SourceBase
from support.site.tving import SupportTving
#########################################################

class SourceTving(SourceBase):
    @classmethod
    def prepare(cls, source_id, source_pw, arg):
        cls.login_data = None

    @classmethod
    def get_channel_list(cls):
        try:
            data = SupportTving.ins.get_live_list(list_type='live', include_drm=ModelSetting.get_bool('tving_include_drm'))
            ret = []
            for item in data:
                c = ModelChannel(cls.source_name, item['id'], item['title'], item['img'], True)
                if item['is_drm']:
                    c.is_drm_channel = True
                c.current = item['episode_title']
                ret.append(c)
        except Exception as e:
            logger.error(f'Exception:{str(e)}')
            logger.error(traceback.format_exc())
        return ret


    @classmethod
    def get_url(cls, source_id, quality, mode):
        try:
            quality = SupportTving.ins.get_quality_to_tving(quality)
            data = SupportTving.ins.get_info(source_id, quality)
            if SupportTving.ins.is_drm_channel(source_id):
                return data
            else:
                return 'return_after_read', data['url']
        except Exception as e:
            logger.error(f'Exception:{str(e)}')
            logger.error(traceback.format_exc())
        

    @classmethod
    def get_return_data(cls, source_id, url, mode):
        try:
            data = requests.get(url).text
            matches = re.finditer(r"BANDWIDTH=(?P<bandwidth>\d+)", data, re.MULTILINE)
            max_bandwidth = 0
            for match in matches:
                bw = int(match.group('bandwidth'))
                if bw > max_bandwidth:
                    max_bandwidth = bw

            temp = url.split('playlist.m3u8')
            url1 = f"{temp[0]}chunklist_b{max_bandwidth}.m3u8{temp[1]}"
            data1 = requests.get(url1).text
            data1 = data1.replace('media', '%smedia' % temp[0]).replace('.ts', '.ts%s' % temp[1])
            if mode == 'web_play':
                data1 = cls.change_redirect_data(data1)
            return data1
        except Exception as e:
            logger.error(f'Exception:{str(e)}')
            logger.error(traceback.format_exc())
        return url
