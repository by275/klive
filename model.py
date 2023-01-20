# -*- coding: utf-8 -*-
#########################################################
# python
import os
import traceback
from datetime import datetime
import json

# third-party
from sqlalchemy import or_, and_, func, not_
from sqlalchemy.orm import backref
from sqlalchemy.orm.attributes import flag_modified

# sjva 공용
from framework import db, path_app_root, app
from framework.util import Util
from plugin import get_model_setting, Logic, default_route

# 패키지
from .plugin import logger, package_name
#########################################################

app.config['SQLALCHEMY_BINDS'][package_name] = 'sqlite:///%s' % (os.path.join(path_app_root, 'data', 'db', '%s.db' % package_name))

ModelSetting = get_model_setting(package_name, logger)


#DB 저장을 이용하지 않는다...
class ModelChannel(db.Model):
    __tablename__ = '%s_channel' % package_name
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = package_name

    id = db.Column(db.Integer, primary_key=True)
    json = db.Column(db.JSON)
    created_time = db.Column(db.DateTime)

    source = db.Column(db.String)
    source_id = db.Column(db.String)
    title = db.Column(db.String)
    icon = db.Column(db.String)
    is_tv = db.Column(db.Boolean)
    current = db.Column(db.String)
    
    is_include_custom = db.Column(db.Boolean)
    is_drm_channel = db.Column(db.Boolean)
    
    def __init__(self, source, source_id, title, icon, is_tv):
        self.source = source
        self.source_id = source_id
        self.title = title
        self.icon = icon
        self.is_tv = is_tv
        self.is_include_custom = False
        self.is_drm_channel = False
        #self.summary = None
        
    def __repr__(self):
        return repr(self.as_dict())

    def as_dict(self):
        ret = {x.name: getattr(self, x.name) for x in self.__table__.columns}
        ret['created_time'] = self.created_time.strftime('%m-%d %H:%M:%S') if ret['created_time'] is not None else None
        if self.json is not None:
            ret['json'] = json.loads(ret['json'])
        else:
            ret['json'] = {}
        return ret

class ModelCustom(db.Model):
    __tablename__ = '%s_custom' % package_name
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = package_name
    

    id = db.Column(db.Integer, primary_key=True)
    json = db.Column(db.JSON)
    created_time = db.Column(db.DateTime)

    source = db.Column(db.String)
    source_id = db.Column(db.String)
    epg_id = db.Column(db.Integer) # 이건 단순히 sort만을 위한거다. 
    epg_name = db.Column(db.String, db.ForeignKey('epg2_channel.name'))
    #epg_name = db.Column(db.String)
    #epg_name2 = db.Column(db.String, db.ForeignKey('epg_channel.name'))
    #epg_entity = db.relationship('ModelEpgMakerChannel', lazy=True)
    title = db.Column(db.String)
    quality = db.Column(db.String)
    number = db.Column(db.Integer)
    #number2 = db.Column(db.Integer)
    group = db.Column(db.String)
    is_drm_channel = db.Column(db.Boolean)

    def __init__(self):
        self.number = 0
        self.created_time = datetime.now()
        self.quality = 'default'
        self.is_drm_channel = False
        
    def __repr__(self):
        return repr(self.as_dict())

    def as_dict(self):
        ret = {x.name: getattr(self, x.name) for x in self.__table__.columns}
        ret['created_time'] = self.created_time.strftime('%m-%d %H:%M:%S') if ret['created_time'] is not None else None
        return ret

    def get_m3u8(self, ddns, mode, apikey):
        tmp = '%s/%s/api/url.m3u8?m=%s&s=%s&i=%s&q=%s' % (ddns, package_name, mode, self.source, self.source_id, self.quality)
        if self.is_drm_channel:
            tmp = tmp.replace('url.m3u8', 'url.mpd')
        if apikey is not None:
            tmp += '&apikey=%s' % apikey
        return tmp
     
    @staticmethod
    def get(source, source_id):
        return db.session.query(ModelCustom).filter_by(source=source).filter_by(source_id=source_id).first()

    
    def set_play_info(self, quality, data):
        try:
            save_data = self.json
            if save_data is None:
                save_data = {}
            save_data[quality] = data
            flag_modified(self, "json")
            db.session.add(self)
            db.session.commit()
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())    
