import sqlite3
import threading
import logging
from datetime import datetime

from flask import Flask, jsonify, json, render_template, request, url_for, redirect, flash
from werkzeug.exceptions import abort

_db_connection_count = 0
_db_lock = threading.Lock()

# Function to get a database connection.
# This function connects to database with the name `database.db`
def get_db_connection():
    global _db_connection_count
    connection = sqlite3.connect('database.db')
    connection.row_factory = sqlite3.Row
    with _db_lock:
        _db_connection_count += 1
    return connection

# Function to get a post using its ID
def get_post(post_id):
    connection = get_db_connection()
    post = connection.execute('SELECT * FROM posts WHERE id = ?',
                        (post_id,)).fetchone()
    connection.close()
    return post

# Define the Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'

# Define the main route of the web application 
@app.route('/')
def index():
    connection = get_db_connection()
    posts = connection.execute('SELECT * FROM posts').fetchall()
    connection.close()
    return render_template('index.html', posts=posts)

# Define how each individual article is rendered 
# If the post ID is not found a 404 page is shown
@app.route('/<int:post_id>')
def post(post_id):
    post = get_post(post_id)
    if post is None:
      app.logger.info(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + f', Post with ID: "{post_id}" does not exists!')
      return render_template('404.html'), 404
    else:
      title = post["title"]
      app.logger.info(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + f', Post: "{title}" was retrieved!')
      return render_template('post.html', post=post)

# Define the About Us page
@app.route('/about')
def about():
    app.logger.info(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + f', "About us" page was retrieved!')
    return render_template('about.html')

@app.route('/healthz')
def healthz():

    conn = None
    try:        
        conn = get_db_connection()        
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='posts';"
        ).fetchone()
        if row is None:
            raise RuntimeError("Missing 'posts' table")       
        conn.execute("SELECT 1 FROM posts LIMIT 1;")

        # Alt ok 200
        return app.response_class(
            response=json.dumps({"result": "OK - healthy"}),
            status=200,
            mimetype="application/json",
        )
    except (sqlite3.Error, RuntimeError) as e:
        # Fejl 
        app.logger.error(
            datetime.now().strftime('%d/%m/%Y, %H:%M:%S')
            + f', /healthz failed: {e}'
        )
        return app.response_class(
            response=json.dumps({"result": "ERROR - unhealthy"}),
            status=500,
            mimetype="application/json",
        )
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass

@app.route('/metrics')
def metrics():
    connection = get_db_connection()
    try:
        row = connection.execute('SELECT COUNT(*) FROM posts').fetchone()
        posts_count = int(row[0]) if row else 0
    finally:
        connection.close()

    return jsonify({
        "db_connection_count": _db_connection_count,
        "post_count": posts_count
    }), 200

# Define the post creation functionality 
@app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            connection = get_db_connection()
            connection.execute('INSERT INTO posts (title, content) VALUES (?, ?)',
                         (title, content))
            connection.commit()
            connection.close()
            app.logger.info(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + f', New post: "{title}" was created!')
            return redirect(url_for('index'))

    return render_template('create.html')

# start the application on port 3111
if __name__ == "__main__":
    import logging
    import sys

    logging.basicConfig(level=logging.INFO)  
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = False            
    
    if not app.logger.handlers:
        app.logger.addHandler(logging.StreamHandler(sys.stdout))

    logging.getLogger('werkzeug').setLevel(logging.INFO)

    app.run(host='0.0.0.0', port='3111')