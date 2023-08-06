# -*- coding: utf-8 -*-
#########################################################
# python
import os
import sys
import logging
import traceback
import json
import re

# third-party
from sqlitedict import SqliteDict
import requests
from flask import redirect

# sjva 공용
from framework import app, db, scheduler, path_app_root, path_data, py_urllib, SystemModelSetting

# 패키지
from .plugin import logger, package_name
from .model import ModelSetting, ModelChannel
from .source_base import SourceBase
import framework.wavve.api as Wavve
from support.base import d
#########################################################



class SourceWavve(SourceBase):
    @classmethod
    def prepare(cls, source_id, source_pw, arg):
        cls.login_data = None

    @classmethod
    def get_channel_list(cls):
        try:
            data = Wavve.live_all_channels()
            ret = []
            for item in data['list']:
                img = 'https://' + item['tvimage'] if item['tvimage'] != '' else ''
                if img != '':
                    tmp = img.split('/')
                    tmp[-1] = py_urllib.quote(tmp[-1].encode('utf8'))
                    img = '/'.join(tmp)
                c = ModelChannel(cls.source_name, item['channelid'], item['channelname'], img, (item['type']=='video'))
                c.current = item['title']
                ret.append(c)
                #logger.debug('%s - %s', item['channelname'], item['tvimage'])
                #if item['channelname'] in ['MBC', 'SBS']:
                #    logger.debug(item)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        return ret

    @classmethod
    def get_url(cls, source_id, quality, mode, retry=True):
        try:
            data = Wavve.streaming('live', source_id, quality)
            surl = None
            if data is not None and 'playurl' in data:
                surl = data['playurl']
                # 2022-01-10 라디오. 대충 함
                #if data['quality'] == '100p' or data['qualities']['list'][0]['name'] == '오디오모드':
                #    surl = data['playurl'].replace('/100/100', '/100') + f"/live.m3u8{data['debug']['orgurl'].split('.m3u8')[1]}"
            if surl is None:
                #logger.debug(d(data))
                #logger.info(f"CH : {source_id}")
                raise Exception('no url')
            if mode == 'web_play':
                return 'return_after_read', surl
            if ModelSetting.get('wavve_streaming_type') == '2':
                return 'redirect', surl
            return 'return_after_read', surl
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())


    @classmethod
    def get_return_data(cls, source_id, url, mode):
        try:
            proxy = Wavve.get_proxy()
            proxies = Wavve.get_proxies()
            headers = {"user-agent": ModelSetting.get("wavve_user_agent")}
            while True:
                data = requests.get(url, proxies=proxies, headers=headers).text
                prefix = url.split('?')[0].rsplit('/', 1)[0]
                if re.findall('\.m3u8\?', data):
                    url = prefix + '/' + data.strip().split('\n')[-1]
                else:
                    break
            new_data = ""
            for line in data.split('\n'):
                line = line.strip()
                if line.startswith != '#' and '.ts' in line:
                    line = f"{prefix}/{line}"
                new_data += f"{line}\n"
            if ModelSetting.get('wavve_streaming_type') == '0': #
                return new_data
            ret = cls.change_redirect_data(new_data, proxy=proxy)
            return ret 
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        return data



    @classmethod
    def make_vod_m3u(cls):
        try:
            from lxml import etree as ET
            from system.model import ModelSetting as SystemModelSetting
            
            data = "#EXTM3U\n"
            root = ET.Element('tv')
            root.set('generator-info-name', "wavve")
            form = '#EXTINF:-1 tvg-id="{contentid}" tvg-name="{title}" tvh-chno="{channel_number}" tvg-logo="" group-title="웨이브 최신 VOD",{title}\n{url}\n'
            ch_number = 1
            for page in range(1, ModelSetting.get_int('wavve_vod_page')+1):
                vod_list = Wavve.vod_newcontents(page=page)['list']
                for info in vod_list:
                    title = info['programtitle']
                    if info['episodenumber'] != '':
                        title += ' (%s회)' % info['episodenumber']
                    tmp = info['episodetitle'].find('Quick VOD')
                    if tmp != -1:
                        title += info['episodetitle'][tmp-2:]

                    video_url = '%s/%s/wavve/api/streaming.m3u8?contentid=%s&type=%s' % (SystemModelSetting.get('ddns'), package_name, info['contentid'], info['type'])    
                    if SystemModelSetting.get_bool('auth_use_apikey'):
                        video_url += '&apikey=%s' % SystemModelSetting.get('auth_apikey')
                    data += form.format(contentid=info['contentid'], title=title, channel_number=ch_number, logo='', url=video_url)

                    channel_tag = ET.SubElement(root, 'channel') 
                    channel_tag.set('id', info['contentid'])
                    #channel_tag.set('repeat-programs', 'true')

                    display_name_tag = ET.SubElement(channel_tag, 'display-name') 
                    display_name_tag.text = '%s(%s)' % (title, ch_number)
                    display_name_tag = ET.SubElement(channel_tag, 'display-number') 
                    display_name_tag.text = str(ch_number)
                    ch_number += 1

            tree = ET.ElementTree(root)
            ret = ET.tostring(root, pretty_print=True, xml_declaration=True, encoding="utf-8")
            return data, ret
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())  


    @classmethod
    def streaming(cls, req):
        try:
            contentid = req.args.get('contentid')
            contenttype = req.args.get('type')
            quality = ModelSetting.get('wavve_quality')
            json_data = Wavve.streaming(contenttype, contentid, quality)
            tmp = json_data['playurl']
            #logger.debug(tmp)
            return redirect(tmp, code=302)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())  

            
