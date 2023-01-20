# -*- coding: utf-8 -*-
#########################################################
# python
import os
import datetime
import traceback
import logging
import subprocess
import time
import re
import json
import requests
import urllib
import lxml.html
import threading
from enum import Enum
from collections import OrderedDict

# third-party
from sqlalchemy import desc
from sqlalchemy import or_, and_, func, not_
from sqlalchemy.orm.attributes import flag_modified

# sjva 공용
from framework import app, db, scheduler, path_app_root, py_unicode, py_urllib
from framework.job import Job
from framework.util import Util

# 패키지
from .plugin import logger, package_name
from .model import ModelSetting, ModelChannel, ModelCustom
from .source_wavve import SourceWavve
from .source_tving import SourceTving
from .source_seezn import SourceSeezn
from .source_streamlink import SourceStreamlink
from .source_youtubedl import SourceYoutubedl
from .source_navertv import SourceNavertv
from .source_kakaotv import SourceKakaotv
from .source_fix_url import SourceFixURL
from .source_kbs import SourceKBS
from .source_sbs import SourceSBS
from .source_mbc import SourceMBC


M3U_FORMAT = '#EXTINF:-1 tvg-id=\"%s\" tvg-name=\"%s\" tvg-logo=\"%s\" group-title=\"%s\" tvg-chno=\"%s\" tvh-chnum=\"%s\",%s\n%s\n' 
M3U_RADIO_FORMAT = '#EXTINF:-1 tvg-id=\"%s\" tvg-name=\"%s\" tvg-logo=\"%s\" group-title=\"%s\" radio=\"true\" tvg-chno=\"%s\" tvh-chnum=\"%s\",%s\n%s\n'


#########################################################

cate_change = {'wavve':'웨이브', 'tving':'티빙', 'seezn':'시즌', 'youtubedl':'YoutubeDL', 'streamlink':'StreamLink', 'navertv':'네이버TV', 'kakaotv':'카카오TV', 'fix_url':'고정주소', 'kbs':'KBS', 'sbs':'SBS', 'mbc':'MBC'}


class LogicKlive(object):
    source_list = None
    channel_list = None

    @staticmethod
    def channel_list2(req):
        try:
            from_site = False
            if 'from_site' in req.form:
                from_site = (req.form['from_site']  == 'true')
            ret = LogicKlive.get_channel_list(from_site=from_site)
            logger.debug('channel_list :%s', len(ret))
            return [x.as_dict() for x in ret]
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def channel_load_from_site():
        try:
            LogicKlive.source_list = OrderedDict()
            if ModelSetting.get_bool('use_wavve'):
                LogicKlive.source_list['wavve'] = SourceWavve('wavve', ModelSetting.get('wavve_id'), ModelSetting.get('wavve_pw'), None)
            if ModelSetting.get_bool('use_tving'):
                LogicKlive.source_list['tving'] = SourceTving('tving', ModelSetting.get('tving_id'), ModelSetting.get('tving_pw'), '0')
            if ModelSetting.get_bool('use_seezn'):
                LogicKlive.source_list['seezn'] = SourceSeezn('seezn', None, None, None)
            #if ModelSetting.get_bool('use_everyon'):
            #    LogicKlive.source_list['everyon'] = SourceEveryon('everyon', None, None, None)
            if ModelSetting.get_bool('use_kbs'):
                LogicKlive.source_list['kbs'] = SourceKBS('kbs', None, None, None)
            if ModelSetting.get_bool('use_mbc'):
                LogicKlive.source_list['mbc'] = SourceMBC('mbc', None, None, None)
            if ModelSetting.get_bool('use_sbs'):
                LogicKlive.source_list['sbs'] = SourceSBS('sbs', None, None, None)
            if ModelSetting.get_bool('use_youtubedl'):
                LogicKlive.source_list['youtubedl'] = SourceYoutubedl('youtubedl', None, None, None)
            if ModelSetting.get_bool('use_streamlink'):
                LogicKlive.source_list['streamlink'] = SourceStreamlink('streamlink', None, None, None)
            if ModelSetting.get_bool('use_navertv'):
                LogicKlive.source_list['navertv'] = SourceNavertv('navertv', None, None, None)
            if ModelSetting.get_bool('use_kakaotv'):
                LogicKlive.source_list['kakaotv'] = SourceKakaotv('kakaotv', None, None, None)
            if ModelSetting.get_bool('use_fix_url'):
                LogicKlive.source_list['fix_url'] = SourceFixURL('fix_url', None, None, None)
            

            LogicKlive.channel_list = []
            for key, source in LogicKlive.source_list.items():
                for i in range(3):
                    tmp = source.get_channel_list()
                    if len(tmp) != 0:
                        break
                    time.sleep(3)
                logger.debug('%s : %s', key, len(tmp))
                for t in tmp:
                    if t.current is not None:
                        t.current = t.current.replace('<', '&lt;').replace('>', '&gt;')
                    LogicKlive.channel_list.append(t)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            
    @staticmethod
    def get_channel_list(from_site=False):
        logger.debug('get_channel_list :%s', from_site)
        try:
            if LogicKlive.channel_list is None or from_site:
                LogicKlive.channel_load_from_site()
            return LogicKlive.channel_list
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())   


    @staticmethod
    def custom():
        try:
            
            # 전체 EPG 목록 채널
            import epg2
            total_channel_list = epg2.ModelEpg2Channel.get_list()
            logger.debug("custom epg channel list : %s", len(total_channel_list))
            tmp = []
            setting_list = db.session.query(ModelSetting).all()
            arg = Util.db_list_to_dict(setting_list)
            for x in total_channel_list:
                if (arg['use_wavve'] == 'True' and x.wavve_id != ''):
                    tmp.append(x)
                elif arg['use_tving'] == 'True' and x.tving_id != '' and (arg['tving_include_drm'] == 'True' or (arg['tving_include_drm']=='True' and 'OCN' not in x.tving_name)):
                    tmp.append(x)
                elif arg['use_seezn'] == 'True' and x.seezn_id != '':
                    if 'OCN' == x.seezn_name and arg['seezn_include_drm']!='True':
                        continue
                    if x.seezn_name in ['VIKI', '미드나잇 채널', '플레이보이 TV', '허니TV'] and arg['seezn_adult']!='True':
                        continue    
                    tmp.append(x)
                        
            
            # 이 목록에 없는 방송은 넣는다.. 스포츠, 라디오?
            # 자동설정
            tmp2 = [x.as_dict() for x in tmp]

            append_list = []
            index = 9000
            for ch in LogicKlive.channel_list:
                find = False
                for t in tmp2:
                    #logger.debug(t)
                    try:
                        if (ch.source == 'wavve' and ch.source_id == t['wavve_id']) or (ch.source == 'tving' and ch.source_id == t['tving_id']) or (ch.source == 'seezn' and ch.source_id == t['seezn_id']): #or (ch.source == 'everyon' and ch.source_id == t['everyon_id']):
                            find = True
                            break
                    except:
                        logger.debug(t)
                if find == False:
                    logger.debug('%s %s' % (ch.source, ch.title))
                    entity = {}
                    index += 1
                    entity['id'] = str(index)
                    entity['name'] = ch.title
                    entity['wavve_name'] = entity['wavve_id'] = entity['wavve_number'] = None
                    entity['tving_name'] = entity['tving_id'] = entity['tving_number'] = None
                    entity['seezn_name'] = entity['seezn_id'] = entity['seezn_number'] = None

                    if ch.source in ['wavve', 'tving', 'seezn']:#, 'everyon']:
                        entity['%s_id' % ch.source] = ch.source_id
                        entity['%s_name' % ch.source] = ch.title
                        entity['category'] = ch.source
                    if ch.source in ['youtubedl', 'streamlink', 'navertv', 'kakaotv', 'fix_url', 'kbs', 'mbc', 'sbs']:
                        entity['user_source'] = ch.source
                        entity['user_source_id'] = ch.source_id
                        entity['user_source_name'] = ch.title
                        entity['auto'] = 'user_source'
                        entity['category'] = cate_change[ch.source]
                    append_list.append(entity)
            logger.debug(u'추가 갯수:%s', len(append_list))
            logger.debug(u'EPG:%s', len(tmp2))
            tmp2 = tmp2 + append_list
            logger.debug(u'TOTAL:%s', len(tmp2))
            #return total_channel_list
            #tmp2 = [x.as_dict() for x in tmp]

            #logger.debug(tmp2)
            for x in tmp2:
                if arg['use_wavve'] == 'True' and x['wavve_id'] != '':
                    x['auto'] = 'wavve'
                elif arg['use_tving'] == 'True' and x['tving_id'] != '':
                    x['auto'] = 'tving'
                elif arg['use_seezn'] == 'True' and x['seezn_id'] != '':
                    x['auto'] = 'seezn'

                if x['wavve_id'] != '':
                    entity = db.session.query(ModelCustom).filter(ModelCustom.source == 'wavve').filter(ModelCustom.source_id == x['wavve_id']).first()
                    if entity is not None:
                        x['wavve_number'] = entity.number
                if x['tving_id'] != '':
                    entity = db.session.query(ModelCustom).filter(ModelCustom.source == 'tving').filter(ModelCustom.source_id == x['tving_id']).first()
                    if entity is not None:
                        x['tving_number'] = entity.number
                if x['seezn_id'] != '':
                    entity = db.session.query(ModelCustom).filter(ModelCustom.source == 'seezn').filter(ModelCustom.source_id == x['seezn_id']).first()
                    if entity is not None:
                        x['seezn_number'] = entity.number
                #if x['everyon_id'] is not None:
                #    entity = db.session.query(ModelCustom).filter(ModelCustom.source == 'everyon').filter(ModelCustom.source_id == x['everyon_id']).first()
                #    if entity is not None:
                #        x['everyon_number'] = entity.number
                if 'user_source' in x:
                    entity = db.session.query(ModelCustom).filter(ModelCustom.source == x['user_source']).filter(ModelCustom.source_id == x['user_source_id']).first()
                    if entity is not None:
                        x['user_source_number'] = entity.number
            return tmp2
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())


    @staticmethod
    def get_url(source, source_id, quality, mode):
        try:
            from .logic import Logic
            if LogicKlive.source_list is None:
                LogicKlive.channel_load_from_site()
            if quality is None or quality == 'default':
                if source == 'wavve':
                    quality = ModelSetting.get('wavve_quality')
                elif source == 'tving':
                    quality = ModelSetting.get('tving_quality')
                elif source == 'seezn':
                    quality = ModelSetting.get('seezn_quality')
            return LogicKlive.source_list[source].get_url(source_id, quality, mode)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())


    @staticmethod
    def get_return_data(source, source_id, url, mode):
        try:
            return LogicKlive.source_list[source].get_return_data(source_id, url, mode)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def get_m3uall():
        try:
            from system.model import ModelSetting as SystemModelSetting
            apikey = None
            if SystemModelSetting.get_bool('auth_use_apikey'):
                apikey = SystemModelSetting.get('auth_apikey')
            m3u = '#EXTM3U\n'
            idx = 1
            for c in LogicKlive.get_channel_list():
                url = '{ddns}/{package_name}/api/url.m3u8?m=url&s={source}&i={source_id}'.format(ddns=SystemModelSetting.get('ddns'), package_name=package_name, source=c.source, source_id=c.source_id)
                if c.is_drm_channel:
                    url = url.replace('url.m3u8', 'url.mpd')
                if apikey is not None:
                    url += '&apikey=%s' % apikey
                if c.is_tv:
                    m3u += M3U_FORMAT % (c.title, c.title, c.icon, cate_change[c.source], idx, idx, f"{c.title}", url)
                else:
                    m3u += M3U_RADIO_FORMAT % (c.title, c.title, c.icon, cate_change[c.source], idx, idx, f"{c.title}", url)
                idx += 1
            return m3u
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod 
    def custom_save(req):
        try:
            ret = {}
            db.session.query(ModelCustom).delete()
            count = 0
            for key, value in req.form.items():
                #logger.debug('Key:%s Value:%s %s', key, value, [key])
                if value == "True":
                    mc = ModelCustom()
                    mc.epg_id, mc.epg_name, mc.group, mc.source, mc.source_id, mc.title, number = key.split('|')
                    mc.epg_name = u'%s' % mc.epg_name
                    mc.title = u'%s' % mc.title
                    mc.group = u'%s' % mc.group
                    if number == 'undefined' or number == 'null':
                        mc.number = 0
                    else:
                        mc.number = int(number)
                    if mc.source == 'tving':
                        from support.site.tving import SupportTving
                        mc.is_drm_channel = SupportTving.ins.is_drm_channel(mc.source_id)
                    if mc.source == 'seezn':
                        # Seezn DRM 채널 추가 시 수정 필요
                        mc.is_drm_channel = (mc.source_id in ['801'])
                    db.session.add(mc)
                    count += 1
            LogicKlive.reset_epg_time()
            db.session.commit()
            ret['ret'] = 'success'
            ret['data'] = count
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
            ret['data'] = str(e)
        return ret

    @staticmethod 
    def get_saved_custom():
        try:
            saved_channeld_list = LogicKlive.get_saved_custom_instance()
            tmp = [x.as_dict() for x in saved_channeld_list]
            return tmp
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod 
    def get_saved_custom_instance():
        try:
            #ret = {}
            query = db.session.query(ModelCustom)
            query = query.order_by(ModelCustom.number)
            query = query.order_by(ModelCustom.epg_id)
            saved_channeld_list = query.all()
            return saved_channeld_list
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod 
    def custom_edit_save(req):
        try:
            count = 0
            for key, value in req.form.items():
                #logger.debug('%s %s', key, value)
                tmp = key.split('|')
                mc = db.session.query(ModelCustom).filter(ModelCustom.source == tmp[0]).filter(ModelCustom.source_id == tmp[1]).with_for_update().first()
                if mc is not None:
                    if tmp[2] == 'quality':
                        mc.quality = value
                    elif tmp[2] == 'number':
                        mc.number = int(value)
                    elif tmp[2] == 'group':
                        mc.group = u'%s' % value
            db.session.commit()            
            LogicKlive.reset_epg_time()
            return LogicKlive.get_saved_custom()
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def reset_epg_time():
        try:
            import epg2
            epg2.Logic.get_module('user').task_interface('klive', 'manual')
            #epg.LogicNormal.make_xml(package_name)
        except Exception as e: 
            #logger.error('Exception:%s', e)
            #logger.error(traceback.format_exc())
            logger.debug('NOT IMPORT EPG!!!')


    @staticmethod 
    def custom_delete(req):
        try:
            ret = {}
            count = 0
            key = req.form['id']
            tmp = key.split('|')
            db.session.query(ModelCustom).filter(ModelCustom.source == tmp[0]).filter(ModelCustom.source_id == tmp[1]).delete()
            db.session.commit()
            return LogicKlive.get_saved_custom()
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def get_m3u(for_tvh=False, m3u_format=None, group=None, call=None):
        try:
            #logger.debug(m3u_format)
            from system.model import ModelSetting as SystemModelSetting
            apikey = None
            if SystemModelSetting.get_bool('auth_use_apikey'):
                apikey = SystemModelSetting.get('auth_apikey')
            ddns = SystemModelSetting.get('ddns')
            m3u = '#EXTM3U\n'
            query = db.session.query(ModelCustom)
            query = query.order_by(ModelCustom.number)
            query = query.order_by(ModelCustom.epg_id)
            saved_channeld_list = query.all()
            
            for c in saved_channeld_list:
                url = '%s/%s/api/url.m3u8?m=url&s=%s&i=%s&q=%s' % (ddns, package_name, c.source, c.source_id, c.quality)
                if c.is_drm_channel:
                    if call == 'kodi':
                        url = url.replace('url.m3u8', 'url.strm')
                    else:
                        url = url.replace('url.m3u8', 'url.mpd')
                if apikey is not None:
                    url += '&apikey=%s' % apikey
                if for_tvh:
                    url = 'pipe://%s -loglevel quiet -i "%s" -c copy -metadata service_provider=sjva_klive -metadata service_name="%s" -c:v copy -c:a aac -b:a 128k -f mpegts -tune zerolatency pipe:1' % ('ffmpeg', url, c.title)

                import epg2
                #ins = epg2.ModelEpg2Channel.get_by_name(c.epg_name)
                ins = epg2.ModelEpg2Channel.get_by_prefer(c.epg_name)
                icon = '' if ins is None else ins.icon
                if icon is None:
                    icon = c.icon
                tvg_name = c.title
                if m3u_format == '1':
                    tvg_name = '%s. %s' % (str(c.number).zfill(3), c.title)
                group_name = c.group
                if group is not None:
                    group_name = '' if group == 'EMPTY' else group
                m3u += M3U_FORMAT % (c.source+'|' + c.source_id, tvg_name, icon, group_name, c.number, c.number, c.title, url)
            return m3u
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def get_m3u_for_sinaplayer():
        try:
            from system.model import ModelSetting as SystemModelSetting
            apikey = None
            if SystemModelSetting.get_bool('auth_use_apikey'):
                apikey = SystemModelSetting.get('auth_apikey')
            ddns = SystemModelSetting.get('ddns')
            m3u = '#EXTM3U\n'
            query = db.session.query(ModelCustom)
            query = query.order_by(ModelCustom.number)
            query = query.order_by(ModelCustom.epg_id)
            saved_channeld_list = query.all()
            
            for c in saved_channeld_list:
                if c.is_drm_channel:
                    play_info = LogicKlive.get_play_info(c.source, c.source_id, c.quality)
                    play_info = json.dumps(play_info)
                else:
                    play_info= '%s/%s/api/url.m3u8?m=url&s=%s&i=%s&q=%s' % (ddns, package_name, c.source, c.source_id, c.quality)
                    if apikey is not None:
                        play_info += '&apikey=%s' % apikey

                import epg2
                ins = epg2.ModelEpg2Channel.get_by_prefer(c.epg_name)
                icon = '' if ins is None else ins.icon
                if icon is None:
                    icon = c.icon
                tvg_name = c.title
                group_name = c.group
                m3u += M3U_FORMAT % (c.source+'|' + c.source_id, tvg_name, icon, group_name, c.number, c.number, c.title, play_info)
            return m3u
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())


    
    @staticmethod
    def get_play_info(source, source_id, quality, mode='url', return_format='json'):
        try:
            from .model import ModelCustom
            db_item = ModelCustom.get(source, source_id)

            # 2020-12-18 아마 한번 얻은 재생정보가 계속 유지할거라고 생각해서 아래 코드작성한것 같음.
            # 한달뒤에 재생 x
            #if db_item is not None and db_item.json is not None and quality in db_item.json:
            #    data = db_item.json[quality]
            #else:
            #    data = LogicKlive.get_url(source, source_id, quality, mode)['play_info']
            #    if db_item is not None:
            #        db_item.set_play_info(quality, data)
            data = LogicKlive.get_url(source, source_id, quality, mode)['play_info']

            if db_item is not None:
                db_item.set_play_info(quality, data)
            if return_format == 'json':
                return data
            elif return_format == 'strm':
                headers = []
                for key, value in data['drm_key_request_properties'].items():
                    headers.append('{key}={value}'.format(key=key, value=py_urllib.quote(value)))
                tmp = """#EXTM3U
#KODIPROP:inputstreamaddon=inputstream.adaptive
#KODIPROP:inputstream.adaptive.license_type=com.widevine.alpha
#KODIPROP:inputstream.adaptive.manifest_type=mpd
#KODIPROP:inputstream.adaptive.license_key={drm_license_uri}|{headers}|R{{SSM}}|
#EXTINF:-1,{ch_name}
{uri}""".format(uri=data['uri'], drm_license_uri=data['drm_license_uri'], headers='&'.join(headers), ch_name=db_item.title)
                return tmp
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
