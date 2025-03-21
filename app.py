from flask import Flask, render_template, request, redirect, url_for, session
import random
import json
import os
import time
from models import db, User, Game, Subject, Question

app = Flask(__name__)
app.secret_key = "supersecretkey"

# 📦 Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///local.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Paths
DATA_DIR = "data"
QUESTIONS_DIR = os.path.join(DATA_DIR, "questions")
USER_TIMES_FILE = os.path.join(DATA_DIR, "user_times.json")
SUBJECTS_FILE = os.path.join(DATA_DIR, "subjects.json")

# Initialize directories
os.makedirs(QUESTIONS_DIR, exist_ok=True)
if not os.path.exists(SUBJECTS_FILE):
    with open(SUBJECTS_FILE, 'w') as f:
        json.dump(["math", "science"], f, indent=4)

# Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "adminpass"

# Game state container
class Game:
    def __init__(self):
        self.board = ['' for _ in range(9)]
        self.subject = "math"
        self.difficulty = "medium"
        self.start_time = None
        self.over = False

    def reset(self):
        self.board = ['' for _ in range(9)]
        self.start_time = time.time()
        self.over = False

game = Game()

# Utilities
def load_subjects():
    with open(SUBJECTS_FILE, "r") as f:
        return json.load(f)

def save_subjects(subjects):
    with open(SUBJECTS_FILE, "w") as f:
        json.dump(subjects, f, indent=4)

def load_questions(subject):
    file_path = os.path.join(QUESTIONS_DIR, f"{subject}.json")
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return []

def save_questions(subject, questions):
    file_path = os.path.join(QUESTIONS_DIR, f"{subject}.json")
    with open(file_path, "w") as f:
        json.dump(questions, f, indent=4)

def load_user_times():
    if os.path.exists(USER_TIMES_FILE):
        with open(USER_TIMES_FILE, "r") as f:
            return json.load(f)
    return {}

def save_user_times(times):
    with open(USER_TIMES_FILE, "w") as f:
        json.dump(times, f, indent=4)

# Routes
@app.route('/', methods=['GET', 'POST'])
def start():
    if request.method == 'POST':
        username = request.form['username']
        difficulty = request.form['difficulty']
        subject = request.form['subject']

        session['username'] = username
        game.difficulty = difficulty
        game.subject = subject
        game.reset()
        return redirect(url_for('play_game'))
    
    subjects = load_subjects()
    return render_template('start.html', subjects=subjects)

@app.route('/play')
def play_game():
    return render_template('index.html', board=game.board, username=session['username'], start_time=game.start_time)

@app.route('/move/<int:index>', methods=['POST'])
def move(index):
    if game.board[index] != '' or game.over:
        return redirect(url_for('play_game'))
    
    questions = load_questions(game.subject)
    print(f"DEBUG: Questions loaded for subject '{game.subject}': {questions}")  # ADD THIS
    if not questions:
        return redirect(url_for('play_game'))

    question = random.choice(questions)
    print(f"DEBUG: Selected question: {question}")  # ADD THIS

    session['move_index'] = index
    session['current_question'] = question
    return render_template('question.html', question=question)

@app.route('/answer', methods=['POST'])
def answer():
    selected_answer = request.form['answer']
    index = session['move_index']
    question = session['current_question']

    if selected_answer == question['answer']:
        game.board[index] = 'X'
        winner = check_winner()
        if winner:
            return end_game(winner)

        ai_auto_move()
        winner = check_winner()
        if winner:
            return end_game(winner)

    return redirect(url_for('play_game'))

def check_winner():
    win_patterns = [
        [0,1,2],[3,4,5],[6,7,8],
        [0,3,6],[1,4,7],[2,5,8],
        [0,4,8],[2,4,6]
    ]
    for pattern in win_patterns:
        a,b,c = pattern
        if game.board[a] == game.board[b] == game.board[c] != '':
            game.over = True
            return session['username'] if game.board[a] == 'X' else 'AI'
    if '' not in game.board:
        game.over = True
        return 'Draw'
    return None

def ai_auto_move():
    empty = [i for i, val in enumerate(game.board) if val == '']
    if not empty: return
    move = random.choice(empty)
    game.board[move] = 'O'

def end_game(winner):
    elapsed_time = round(time.time() - game.start_time, 2)
    username = session['username']
    times = load_user_times()
    result = "WON" if winner == username else "LOST" if winner == "AI" else "DRAW"
    times.setdefault(username, []).append(f"Game {len(times.get(username, [])) +1}: {elapsed_time}s ({result})")
    save_user_times(times)
    return render_template(
    'winner.html',
    winner=winner,
    board=game.board,
    time=elapsed_time,
    history=times[username],
    username=username,
    all_histories=times  # Send all user data
)


# Admin Routes
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user = request.form['username']
        pw = request.form['password']
        if user == ADMIN_USERNAME and pw == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin_panel'))
    return render_template('admin_login.html')

@app.route('/admin_panel', methods=['GET', 'POST'])
def admin_panel():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    subjects = load_subjects()
    questions = {}
    for subject in subjects:
        questions[subject] = load_questions(subject)
    
    return render_template('admin_panel.html', subjects=subjects, questions=questions)

@app.route('/admin/add_subject', methods=['POST'])
def add_subject():
    new_subject = request.form['new_subject']
    subjects = load_subjects()
    if new_subject not in subjects:
        subjects.append(new_subject)
        save_subjects(subjects)
    return redirect(url_for('admin_panel'))

@app.route('/admin/add_question', methods=['POST'])
def add_question():
    subject = request.form['subject']
    question_text = request.form['question']
    choices = [request.form['choice1'], request.form['choice2'], request.form['choice3'], request.form['choice4']]
    answer = request.form['answer']
    question = {"question": question_text, "choices": choices, "answer": answer}

    questions = load_questions(subject)
    questions.append(question)
    save_questions(subject, questions)
    return redirect(url_for('admin_panel'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('start'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

