from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String)
    email = db.Column(db.String, unique=True)
    password = db.Column(db.String(225))
    is_verified = db.Column(db.Boolean, default=False)


class FavoriteServers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    server_id = db.Column(db.Integer, db.ForeignKey('servers.id'))

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String)
    uuid = db.Column(db.String)

class PlayersPrivileges(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    privilege_id = db.Column(db.Integer)

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('user.id'))
    rule = db.Column(db.Integer)
    approved = db.Column(db.Boolean)

class Servers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String)

class ServersUsersPerms(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('servers.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    perm_id = db.Column(db.Integer)

def generateDB(app):
    with app.app_context():
        db.create_all()

def resetDB(app):
    with app.app_context():
        db.drop_all()
        db.create_all()

