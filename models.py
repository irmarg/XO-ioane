from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# 🧑 User Table
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    games = db.relationship('Game', backref='player', lazy=True)

# 🎮 Game Table
class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    time_taken = db.Column(db.Float, nullable=False)
    result = db.Column(db.String(10), nullable=False)  # "WON" or "LOST"
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# 📚 Subject Table
class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    questions = db.relationship('Question', backref='subject', lazy=True)

# ❓ Question Table
class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    question_text = db.Column(db.String(300), nullable=False)
    choice1 = db.Column(db.String(100), nullable=False)
    choice2 = db.Column(db.String(100), nullable=False)
    choice3 = db.Column(db.String(100), nullable=False)
    choice4 = db.Column(db.String(100), nullable=False)
    correct_answer = db.Column(db.String(100), nullable=False)
