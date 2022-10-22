import sqlite3
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class sentencesJP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sentence = db.Column(db.Text)
    transcription = db.Column(db.Text)
    tokens = db.Column(db.Text)
    grade = db.Column(db.Integer)
    frequency = db.Column(db.Integer)

class sentencesCN(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sentence = db.Column(db.Text)
    transcription = db.Column(db.Text)
    tokens = db.Column(db.Text)
    grade = db.Column(db.Integer)
    frequency = db.Column(db.Integer)

class sentencesEN(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sentence = db.Column(db.Text)

class transJP_EN(db.Model):
    jp_id = db.Column(db.Integer, db.ForeignKey(sentencesJP.id), primary_key=True)
    en_id = db.Column(db.Integer, db.ForeignKey(sentencesEN.id))

class transCN_EN(db.Model):
    cn_id = db.Column(db.Integer, db.ForeignKey(sentencesCN.id), primary_key=True)
    en_id = db.Column(db.Integer, db.ForeignKey(sentencesEN.id))

class transJP_CN(db.Model):
    jp_id = db.Column(db.Integer, db.ForeignKey(sentencesJP.id), primary_key=True)
    cn_id = db.Column(db.Integer, db.ForeignKey(sentencesCN.id))

class dictionaryJP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.Text)
    transcription = db.Column(db.Text)
    definition = db.Column(db.Text)
    pos = db.Column(db.Text)

class levelJP(db.Model):
    dict_id = db.Column(db.Integer, db.ForeignKey(dictionaryJP.id), primary_key=True)
    grade = db.Column(db.Integer)
    frequency = db.Column(db.Integer)

class dictionaryCN(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.Text)
    transcription = db.Column(db.Text)
    definition = db.Column(db.Text)

class levelCN(db.Model):
    dict_id = db.Column(db.Integer, db.ForeignKey(dictionaryCN.id), primary_key=True)
    grade = db.Column(db.Integer)
    frequency = db.Column(db.Integer)