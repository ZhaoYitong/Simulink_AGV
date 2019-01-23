from application import db
from datetime import datetime


class Container(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(100), nullable=True)
    flag = db.Column(db.Integer, nullable=False)
    bay = db.Column(db.Integer, nullable=True)
    cycle_bay = db.Column(db.Integer, nullable=True)
    yard = db.Column(db.Integer, nullable=True)
    cycle_yard = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return '<Container_%s>' % self.id


class QC(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(100), nullable=True)
    position = db.Column(db.Integer, nullable=False)
    lanes = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return '<QC_%s>' % self.id


class ARMG(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(100), nullable=True)
    position = db.Column(db.Integer, nullable=False)
    lanes = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return '<ARMG_%s>' % self.id


class AGV(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(100), nullable=True)
    position = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return '<AGV_%s>' % self.id


class Preset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(100), nullable=True)
    factor = db.Column(db.Float, nullable=False)
    num_qc = db.Column(db.Integer, nullable=False)
    num_armg = db.Column(db.Integer, nullable=False)
    num_agv = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)


class Sim(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qcs = db.Column(db.String(100), nullable=False)
    armgs = db.Column(db.String(100), nullable=False)
    agvs = db.Column(db.String(100), nullable=False)
    containers = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)


tags = db.Table('tags',
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id')),
    db.Column('page_id', db.Integer, db.ForeignKey('page.id'))
)

class Page(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tags = db.relationship('Tag', secondary=tags,
        backref=db.backref('pages', lazy='dynamic'))

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
