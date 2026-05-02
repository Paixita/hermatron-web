from flask import Flask, render_template, jsonify
import sqlite3

app = Flask(__name__)
DB_NAME = "cine.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/movies')
def get_movies():
    conn = get_db_connection()
    movies = conn.execute('SELECT * FROM movies WHERE status = "published"').fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in movies])

if __name__ == '__main__':
    # Puerto diferente al de Hermatron (5000) para evitar conflictos
    print("🎬 Iniciando servidor de Cine_panita en http://localhost:5005")
    app.run(port=5005, debug=True)
