import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",          # your mysql username
        password="Danie@24",
        database="aviation_db"
    )