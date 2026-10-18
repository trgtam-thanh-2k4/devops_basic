import os
import time

import pymysql
from flask import Flask, jsonify, request

app = Flask(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "admin"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "appdb"),
    "cursorclass": pymysql.cursors.DictCursor,
    "connect_timeout": 5,
}


def get_conn():
    return pymysql.connect(**DB_CONFIG)


def init_db(retries=10):
    # RDS/MySQL may not be ready when the container starts, so retry
    for attempt in range(1, retries + 1):
        try:
            with get_conn() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        email VARCHAR(100) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                conn.commit()
            print("Database initialized")
            return
        except pymysql.MySQLError as e:
            print(f"DB not ready (attempt {attempt}/{retries}): {e}")
            time.sleep(3)
    print("Could not initialize database, continuing anyway")


@app.get("/")
def index():
    return jsonify(message="Hello from ECS!", endpoints=["/health", "/users"])


@app.get("/health")
def health():
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT VERSION() AS version")
            version = cur.fetchone()["version"]
        return jsonify(status="ok", db="connected", mysql_version=version)
    except pymysql.MySQLError as e:
        return jsonify(status="error", db="disconnected", error=str(e)), 500


@app.get("/users")
def list_users():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, name, email, created_at FROM users ORDER BY id")
        return jsonify(cur.fetchall())


@app.post("/users")
def create_user():
    data = request.get_json(silent=True) or {}
    if not data.get("name") or not data.get("email"):
        return jsonify(error="name and email are required"), 400
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (name, email) VALUES (%s, %s)",
            (data["name"], data["email"]),
        )
        conn.commit()
        new_id = cur.lastrowid
    return jsonify(id=new_id, name=data["name"], email=data["email"]), 201


@app.delete("/users/<int:user_id>")
def delete_user(user_id):
    with get_conn() as conn, conn.cursor() as cur:
        affected = cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
    if not affected:
        return jsonify(error="user not found"), 404
    return jsonify(deleted=user_id)


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
