# -*- coding: utf-8 -*-
#########################################################
# python
import os
import sys
import logging
import traceback
import json
import ssl
import datetime
import xml.etree.ElementTree as ET
import re

# third-party
from sqlitedict import SqliteDict
import requests
# sjva 공용
from framework.logger import get_logger
from framework import app, db, scheduler, path_app_root, path_data, py_urllib, py_urllib2
from system.logic import SystemLogic

# 패키지
from .model import ModelSetting, ModelChannel
from .source_base import SourceBase

# 로그
package_name = __name__.split('.')[0]
logger = get_logger(package_name)
#########################################################


class SourceEveryon(SourceBase):
    EVERYON_LIST = ['전체채널|all', '종편/뉴스|20100', '시리즈/영화/다큐|20200', '예능/스포츠/레저|20300', '증권/음악/여성|20400', '어린이/지역채널|20500', '정보/종교|20600']

    @classmethod
    def prepare(cls, source_id, source_pw, arg):
        pass
   
    
    @classmethod
    def get_channel_list(cls):
        try:
            ret = []
            for cate in cls.EVERYON_LIST:
                temp = cate.split('|')
                if temp[1] != 'all':
                    pageNo = 1
                    while True:
                        hasMore, cate_list = cls.GetChannelListFromCate(temp[1], pageNo)
                        for item in cate_list:
                            #ret.append(item)
                            tmp = item['title'].split(' ')
                            title = ' '.join(tmp[1:])
                            # GODTV, 
                            if item['id'] in ['409', '435', '547']:
                                continue
                            c = ModelChannel(cls.source_name, 
                                item['id'], 
                                title, 
                                item['img'],
                                True)
                            #c.current = item.findtext('description')
                            ret.append(c)

                        if hasMore == 'N': break
                        pageNo += 1
            return ret

        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        return ret
    
    @classmethod
    def GetChannelListFromCate(cls, cate, pageNo='1'):
        url  = 'http://www.hcnmobile.tv/main/proc/ajax_ch_list.php'
        params = { 'chNum' : '', 'cate':'', 'sCate':cate, 'chNum':'', 'chNm':'', 'page':pageNo, 'perPage':'20', 'srchTxt':''  }
        postdata = py_urllib.urlencode( params )
        request = py_urllib2.Request(url, postdata)
        request.add_header('Cookie', 'etv_api_key=88abc0e1c8e61c8c3109788ec8392c7fd86c16765fc0b80d5f2366c84c894203')
        response = py_urllib2.urlopen(request)
        data = response.read()
        hasMore = 'Y' if int(data.split('|')[1]) > int(pageNo) * 20 else 'N'
        regax = 'thumb\"\stitle\=\"(.*?)\".*\s*.*selCh\(\'(.*?)\'.*\s*<img\ssrc\=\"(.*?)\"'
        regax2 = 'ch_name\"\stitle\=\"(.*?)\"'
        r = re.compile(regax)
        r2 = re.compile(regax2)
        m = r.findall(data)
        m2 = r2.findall(data)
        list = []
        #for item in m:
        for i in range(len(m)):
            info = {}
            info['title'] = m[i][0].replace(',', ' ')
            info['id'] = m[i][1]
            info['img'] = m[i][2]
            info['summary'] = m2[i]
            list.append(info)
        logger.debug('ret:%s %s', hasMore, len(list))
        return hasMore, list



    @classmethod
    def get_url(cls, source_id, quality, mode):
        #logger.debug('EVERYON get_url:%s %s', source_id, quality)
        try:
            url  = 'http://www.hcnmobile.tv/main/proc/get_ch_data.php'
            params = { 'chId' : source_id }
            postdata = py_urllib.urlencode( params )
            request = py_urllib2.Request(url, postdata)
            request.add_header('Cookie', 'etv_api_key=88abc0e1c8e61c8c3109788ec8392c7fd86c16765fc0b80d5f2366c84c894203')
            response = py_urllib2.urlopen(request)
            data = json.load(response, encoding='utf8') if sys.version_info[0] == 2 else json.load(response)
            #url2 = data['medias'][0]['url'] if len(data['medias']) > 0 else None	
            url2 = data['media']['url'].replace('\\','')
            #logger.debug('EVERYON22 :%s', url2)

            cookie = response.info().getheader('Set-Cookie')
            if cookie is None:
                # 종편
                req = py_urllib2.Request(url2)
                res = py_urllib2.urlopen(req)
                data = res.read()
                match = re.compile(r'chunklist(?P<tmp>.*?)$').search(data)
                if match:
                    redirect_url = '%schunklist%s' % (url2.split('playlist.m3u8')[0], match.group('tmp'))
                    return 'redirect', redirect_url
                    #return 'return_after_read', redirect_url
            else:
                #logger.debug('EVERYON22 cookie :%s', cookie)
                ret = url2
                info = {}
                info['Key-Pair-Id'] = ''
                info['Policy'] = ''
                info['Signature'] = ''

                for c in cookie.split(','):
                    c = c.strip()
                    if c.startswith('CloudFront-Key-Pair-Id'):
                        info['Key-Pair-Id'] = c.split(';')[0].split('=')[1]
                    if c.startswith('CloudFront-Policy'):
                        info['Policy'] = c.split(';')[0].split('=')[1]
                    if c.startswith('CloudFront-Signature'):
                        info['Signature'] = c.split(';')[0].split('=')[1]
                ret = ret.replace('live.m3u8', 'live_hd.m3u8')
                #tmp = 'Key-Pair-Id=%s;Policy=%s;Signature=%s' % (info['Key-Pair-Id'], info['Policy'], info['Signature'])
                ret = '%s?Key-Pair-Id=%s&Policy=%s&Signature=%s' % (ret, info['Key-Pair-Id'], info['Policy'], info['Signature'])
                return 'return_after_read', ret
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        

    
    @classmethod
    def get_return_data(cls, source_id, url, mode):
        try:
            #logger.debug(url)
            tmps = url.split('?')
            pre = '/'.join ( tmps[0].split('/')[:-1]) + '/'
            post = tmps[1]

            req = py_urllib2.Request(url)
            res = py_urllib2.urlopen(req)
            data = res.read()
            #logger.debug(data)
            #index_list = ['index_576p30.m3u8', 'index_hd.m3u8']
            #for index in index_list:
            if data.find('index_576p30.m3u8') != -1 or data.find('index_hd.m3u8') != -1:
                url = url.replace('index.m3u8', 'index_576p30.m3u8')
                url = url.replace('index.m3u8', 'index_hd.m3u8')
                
                req = py_urllib2.Request(url)
                res = py_urllib2.urlopen(req)
                data = res.read()
                #logger.debug(data)
                data = re.sub('index_576p30', pre+'index_576p30', data)
                data = re.sub('index_hd', pre+'index_hd', data)
                data = re.sub('.ts', '.ts?' + post, data)
                return data
            else:
                data = re.sub('live', pre+'live', data)
                data = re.sub('.ts', '.ts?' + post, data)
                data = re.sub('chunklist', pre+'chunklist', data)
            #if mode == 'lc' or mode == 'url':
            if data.find('chunklist') == -1:
                if mode == 'web_play':
                    data = cls.change_redirect_data(data)
                return data
            else:
                logger.debug('YYYYYYYYYYYYYYYYYYYYYYYYYY')
                match = re.search('http(.*?)$' ,data)
                if match:
                    req = py_urllib2.Request(match.group(0))
                    res = py_urllib2.urlopen(req)
                    data = res.read()
                    result = re.compile('(.*?)\.ts').findall(data)
                    for r in result:
                        data = data.replace(r, '%s%s' % (pre, r))
                    return data
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    """
    def MakeEPG(self, prefix, channel_list=None):
		list = self. GetChannelList()
		#list = list[2:3]
		import datetime
		startDate = datetime.datetime.now()
		startParam = startDate.strftime('%Y%m%d')
		endDate = startDate + datetime.timedelta(days=1)
		endParam = endDate.strftime('%Y%m%d')

		str = ''
		regax = '\<td\>(.*?)\<'
		p = re.compile(regax)

		count = 700
		type_count = 0
		for item in list:
			count += 1
			channel_number = count
			channel_name = item['title']
			if channel_list is not None:
				if len(channel_list['EVERYON']) == type_count: break
				if item['id'] in channel_list['EVERYON']:
					type_count += 1
					channel_number = channel_list['EVERYON'][item['id']]['num']
					if len(channel_list['EVERYON'][item['id']]['name']) is not 0: channel_name = channel_list['EVERYON'][item['id']]['name']
				else:
					continue

			str += '\t<channel id="EVERYON|%s" video-src="%slc&type=EVERYON&id=%s" video-type="HLS">\n' % (item['id'], prefix, item['id'])
			str += '\t\t<display-name>%s</display-name>\n' % channel_name
			str += '\t\t<display-name>%s</display-name>\n' % channel_number
			str += '\t\t<display-number>%s</display-number>\n' % channel_number
			str += '\t\t<icon src="%s" />\n' % item['img']
			str += '\t</channel>\n'

			url_today = 'http://www.everyon.tv/main/schedule.etv?chNum=%s' % item['id']
			url_next = 'http://www.everyon.tv/main/schedule.etv?chNum=%s&schDt=%s&schFlag=n' % (item['id'], startParam)

			#continue

			for url in [url_today, url_next]:
				current_date = startDate if url == url_today else endDate

				request = py_urllib2.Request(url)
				response = py_urllib2.urlopen(request)
				data = response.read()
				idx1 = data.find('<tbody>')
				idx2 = data.find('</tbody>')
				data = data[idx1+7:idx2]
				
				m = p.findall(data)
				for i in range(len(m)/3):
					time2 = m[i*3].replace(':', '')
					title = m[i*3+1]
					age = m[i*3+2]
					
					if time2 == '': continue

					temp = time2.split('~')
					start_time = temp[0]
					end_time = temp[1]
					start_str = '%s%s' % (current_date.strftime('%Y%m%d'),start_time)
					if int(start_time) > int(end_time): current_date = current_date + datetime.timedelta(days=1)
					end_str = '%s%s' % (current_date.strftime('%Y%m%d'),end_time)
					if long(start_str) >= long(end_str): continue
					str += '\t<programme start="%s00 +0900" stop="%s00 +0900" channel="EVERYON|%s">\n' %  (start_str, end_str, item['id'])
					str += '\t\t<title lang="kr">%s</title>\n' % title.replace('<',' ').replace('>',' ')
					
					age_str = '%s세 이상 관람가' % age if age != 'ALL' else '전체 관람가'
					str += '\t\t<rating system="KMRB"><value>%s</value></rating>\n' % age_str
					desc = '등급 : %s\n' % age_str

					str += '\t\t<desc lang="kr">%s</desc>\n' % desc.strip().replace('<',' ').replace('>',' ')
					str += '\t</programme>\n'
				time.sleep(SLEEP_TIME)
		return str
    """