import sqlite3
import uuid
from datetime import datetime

DB_NAME = "cine.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Crear la tabla de películas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS movies (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        slug TEXT NOT NULL UNIQUE,
        description TEXT,
        poster_url TEXT,
        backdrop_url TEXT,
        category TEXT,
        year INTEGER,
        rating REAL,
        duration INTEGER,
        embed_url TEXT,
        views INTEGER DEFAULT 0,
        is_featured BOOLEAN DEFAULT 0,
        status TEXT DEFAULT 'published',
        created_at TIMESTAMP
    )
    ''')
    
    # Insertar datos de prueba si la tabla está vacía
    cursor.execute('SELECT COUNT(*) FROM movies')
    if cursor.fetchone()[0] == 0:
        sample_movies = [
            (str(uuid.uuid4()), "El Gran Hackeo", "el-gran-hackeo", "Un documental sobre datos y privacidad.", "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5", "https://images.unsplash.com/photo-1518770660439-4636190af475", "Documental, Tecnología", 2024, 8.5, 114, "https://www.youtube.com/embed/dQw4w9WgXcQ", 1500, True, 'published', datetime.now()),
            (str(uuid.uuid4()), "Odisea Espacial", "odisea-espacial", "Un viaje más allá de las estrellas.", "https://images.unsplash.com/photo-1451187580459-43490279c0fa", "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa", "Ciencia Ficción", 2025, 9.2, 140, "https://www.youtube.com/embed/dQw4w9WgXcQ", 3200, False, 'published', datetime.now()),
            (str(uuid.uuid4()), "Operación Escape", "operacion-escape", "Acción sin frenos en la ciudad.", "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9", "https://images.unsplash.com/photo-1461800919507-79b16743b257", "Acción", 2023, 7.8, 95, "https://www.youtube.com/embed/dQw4w9WgXcQ", 800, False, 'published', datetime.now())
        ]
        
        cursor.executemany('''
        INSERT INTO movies (id, title, slug, description, poster_url, backdrop_url, category, year, rating, duration, embed_url, views, is_featured, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_movies)
        print("✅ Películas de prueba insertadas con éxito.")
    
    conn.commit()
    conn.close()
    print("✅ Base de datos 'Cine_panita' inicializada correctamente.")

if __name__ == '__main__':
    init_db()
