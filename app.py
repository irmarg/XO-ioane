from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os, random, time
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///local.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User Table
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    games = db.relationship('Game', backref='player', lazy=True)

# Game Table
class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    time_taken = db.Column(db.Float, nullable=False)
    result = db.Column(db.String(10), nullable=False)  # "WON" or "LOST"
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Subject Table
class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    questions = db.relationship('Question', backref='subject', lazy=True)

# Question Table
class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    question_text = db.Column(db.String(300), nullable=False)
    choice1 = db.Column(db.String(100), nullable=False)
    choice2 = db.Column(db.String(100), nullable=False)
    choice3 = db.Column(db.String(100), nullable=False)
    choice4 = db.Column(db.String(100), nullable=False)
    correct_answer = db.Column(db.String(100), nullable=False)

# Game Logic (in-memory)
class GameState:
    def __init__(self):
        self.board = [''] * 9
        self.subject_id = None
        self.start_time = None
        self.over = False

    def reset(self):
        self.board = [''] * 9
        self.start_time = time.time()
        self.over = False

game_state = GameState()

# Routes
@app.route('/', methods=['GET', 'POST'])
def start():
    if request.method == 'POST':
        username = request.form['username']
        subject_id = request.form['subject']
        difficulty = request.form['difficulty']  # ✅ Capture difficulty

        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username)
            db.session.add(user)
            db.session.commit()

        session['username'] = user.username
        session['user_id'] = user.id
        session['difficulty'] = difficulty  # ✅ Store in session for later
        game_state.subject_id = int(subject_id)
        game_state.reset()
        return redirect(url_for('play_game'))

    subjects = Subject.query.all()
    return render_template('start.html', subjects=subjects)

@app.route('/play')
def play_game():
    return render_template('index.html', board=game_state.board, username=session['username'], start_time=game_state.start_time)

@app.route('/move/<int:index>', methods=['POST'])
def move(index):
    if game_state.board[index] != '' or game_state.over:
        return redirect(url_for('play_game'))

    questions = Question.query.filter_by(subject_id=game_state.subject_id).all()
    if not questions:
        return redirect(url_for('play_game'))

    question = random.choice(questions)
    session['move_index'] = index
    session['question_id'] = question.id
    return render_template('question.html', question=question)

@app.route('/answer', methods=['POST'])
def answer():
    selected = request.form['answer']
    question = Question.query.get(session['question_id'])

    if selected == question.correct_answer:
        idx = session['move_index']
        game_state.board[idx] = 'X'
        winner = check_winner()
        if winner:
            return end_game(winner)
        ai_move()
        winner = check_winner()
        if winner:
            return end_game(winner)
    return redirect(url_for('play_game'))

def ai_move():
    empty = [i for i, v in enumerate(game_state.board) if v == '']
    if empty:
        move = random.choice(empty)
        game_state.board[move] = 'O'

def check_winner():
    wins = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]]
    for a,b,c in wins:
        if game_state.board[a] == game_state.board[b] == game_state.board[c] != '':
            game_state.over = True
            return session['username'] if game_state.board[a] == 'X' else 'AI'
    if '' not in game_state.board:
        game_state.over = True
        return 'Draw'
    return None

def end_game(winner):
    elapsed = round(time.time() - game_state.start_time, 2)
    result = "WON" if winner == session['username'] else "LOST"
    game = Game(user_id=session['user_id'], time_taken=elapsed, result=result)
    db.session.add(game)
    db.session.commit()

    user_games = Game.query.filter_by(user_id=session['user_id']).all()
    all_games = Game.query.all()

    return render_template('winner.html', winner=winner, time=elapsed, user_games=user_games, all_games=all_games, username=session['username'])

# Admin Login
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        pw = request.form['password']
        if username == "admin" and pw == "adminpass":
            session['admin'] = True
            return redirect(url_for('admin_panel'))
        else:
            return render_template('admin_login.html', error="Invalid credentials")
    return render_template('admin_login.html')
#admin panel
@app.route('/admin_panel', methods=['GET', 'POST'])
def admin_panel():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    subjects = Subject.query.all()
    questions = Question.query.all()
    return render_template('admin_panel.html', subjects=subjects, questions=questions)
# Add Subject
@app.route('/add_subject', methods=['POST'])
def add_subject():
    name = request.form['new_subject']
    if not Subject.query.filter_by(name=name).first():
        subject = Subject(name=name)
        db.session.add(subject)
        db.session.commit()
    return redirect(url_for('admin_panel'))
# Add Question
@app.route('/add_question', methods=['POST'])
def add_question():
    subject_id = int(request.form['subject'])
    q = Question(
        subject_id=subject_id,
        question_text=request.form['question'],
        choice1=request.form['choice1'],
        choice2=request.form['choice2'],
        choice3=request.form['choice3'],
        choice4=request.form['choice4'],
        correct_answer=request.form['answer']
    )
    db.session.add(q)
    db.session.commit()
    return redirect(url_for('admin_panel'))
#delete question
@app.route('/delete_question/<int:qid>', methods=['POST'])
def delete_question(qid):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    q = Question.query.get_or_404(qid)
    db.session.delete(q)
    db.session.commit()
    return redirect(url_for('admin_panel'))
#edit question
@app.route('/edit_question/<int:qid>', methods=['POST'])
def edit_question(qid):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    q = Question.query.get_or_404(qid)
    new_text = request.form['new_text']
    q.question_text = new_text
    db.session.commit()
    return redirect(url_for('admin_panel'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('start'))

# Run db.create_all() at app startup (for Render + local)
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
