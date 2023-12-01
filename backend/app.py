from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import re
import random
from random import randint
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)

database_config = {
    'host': 'mysql-service',
    # 'host': 'localhost',
    'user': 'root',
    'password': os.environ.get('MYSQL_ROOT_PASSWORD'),
    'database': 'mydatabase'
}
my_database = mysql.connector.connect(**database_config)
cursor = my_database.cursor()
query = """
    CREATE TABLE IF NOT EXISTS api_keys (
        id INT AUTO_INCREMENT PRIMARY KEY,
        email VARCHAR(255) NOT NULL,
        `key` VARCHAR(255) NOT NULL)
    """
cursor.execute(query)
query = """
CREATE TABLE IF NOT EXISTS weather_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL,
    temperature INT NOT NULL,
    humidity INT NOT NULL,
    windSpeed INT NOT NULL,
    `condition` VARCHAR(255) NOT NULL DEFAULT 'sunny',
    UNIQUE(date)
);
"""
cursor.execute(query)

def generate_random_api_key(length=16):
    return ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(length))

def add_to_database(email, key):
    query = "INSERT INTO api_keys (`key`, email) VALUES (%s, %s)"
    cursor.execute(query, (key, email))
    my_database.commit()

def key_exists(key):
    query = "SELECT COUNT(*) FROM api_keys WHERE `key` = %s"
    cursor.execute(query, (key,))
    return cursor.fetchone()[0] > 0

def get_key_by_email(email):
    query = "SELECT `key` FROM api_keys WHERE email = %s"
    cursor.execute(query, (email,))
    result = cursor.fetchone()
    return "" if result is None else result[0]

def generate_unique_api_key():
    while True:
        new_key = generate_random_api_key()
        if not key_exists(new_key):
            return new_key

@app.route('/weather/multi-day', methods=['GET'])
def get_multi_day_weather():
    api_key = request.headers.get('Api-Key')
    if not api_key or not key_exists(api_key):
        return jsonify({"error": "Invalid or missing API key"}), 401
    print(api_key)
    num_days = request.args.get('days', default=1, type=int)
    start_date = datetime.now().date() - timedelta(days=num_days - 1)

    weather_data = []
    for i in range(num_days):
        date = start_date + timedelta(days=i)
        cursor.execute("SELECT temperature, humidity, windSpeed, `condition` FROM weather_data WHERE date = %s", (date,))
        result = cursor.fetchone()

        if not result:
            # Generate random weather data
            temperature = randint(0, 30)
            humidity = randint(20, 80)
            windSpeed = randint(0, 10)
            condition = random.choice(['sunny', 'rainy', 'stormy', 'cloudy', 'snowy'])
            cursor.execute("INSERT INTO weather_data (date, temperature, humidity, windSpeed, `condition`) VALUES (%s, %s, %s, %s, %s)",
                           (date, temperature, humidity, windSpeed, condition))
            my_database.commit()
            result = (temperature, humidity, windSpeed, condition)

        weather_data.append({
            "date": date.strftime("%Y-%m-%d"),
            "temperature": result[0],
            "humidity": result[1],
            "windSpeed": result[2],
            "condition": result[3]
        })

    return jsonify(weather_data)

@app.route('/generate', methods=['GET'])
def generate_api_key():
    email = request.headers.get('email')
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return "Invalid email format", 400
    key = get_key_by_email(email)
    if(key == ""):
        key = generate_unique_api_key()
        add_to_database(email,key)
    return key

if __name__ == '__main__':
    app.run(host="0.0.0.0")
