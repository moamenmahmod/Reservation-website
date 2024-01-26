import sqlite3
from sqlite3 import Error
from database import *
import hashlib
import secrets
from flask import Flask, app , render_template , request  , redirect, url_for, session,flash,abort,jsonify,render_template_string
from werkzeug.utils import secure_filename
import os


def createDBconnection(name="cinema.db"):
    return sqlite3.connect(name, check_same_thread=False)

def init_db(connection):
    data = connection.cursor()

    data.execute('''
        CREATE TABLE IF NOT EXISTS users (
            userid INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            photo TEXT DEFAULT 'default.png',
            isadmin INTEGER DEFAULT 0,
            token TEXT UNIQUE
        )
    ''')


    data.execute('''
        CREATE TABLE IF NOT EXISTS films (
            filmid INTEGER PRIMARY KEY AUTOINCREMENT,
            filmname TEXT NOT NULL UNIQUE,
            genre TEXT NOT NULL ,
            photo TEXT ,
            price INTEGER NOT NULL,
            availabletickets INTEGER NOT NULL,
            soldout INTEGER DEFAULT 0
        )
    ''')


    data.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            commentid iNTEGER PRIMARY KEY AUTOINCREMENT,
            userid INTEGER,
            comment TEXT NOT NULL,
            filmname TEXT NOT NULL,
            username TEXT NOT NULL,
            userphoto TEXT ,
            FOREIGN KEY (userid) REFERENCES users(userid) ON DELETE CASCADE,
            FOREIGN KEY (filmname) REFERENCES films(filmname) ON DELETE CASCADE
        )
    ''')

    connection.commit()

def generate_token():
    return secrets.token_urlsafe(32)  


def hash_password(password):
    # Create a new SHA-256 hash object
    sha256 = hashlib.sha256()
    
    # Update the hash object with the password bytes
    sha256.update(password.encode('utf-8'))
    
    # Return the hashed password as a hexadecimal string
    return sha256.hexdigest()


def registerU(username, email, password):
    # Hash the password before storing it in the database
    hashed_password = hash_password(password)
    
    # Connect to the SQLite database using a context manager
    with createDBconnection() as conn:
        data = conn.cursor()
        
        query = '''
        INSERT INTO users (username, email, password)
        VALUES (?, ?, ?)
        '''
        if data.execute(query, (username, email, hashed_password)) == True :
            return True
        else:
            return False
        



def registerUA(username, email, password,admin):
    # Hash the password before storing it in the database
    hashed_password = hash_password(password)
    
    # Connect to the SQLite database using a context manager
    with createDBconnection() as conn:
        data = conn.cursor()
        
        query = '''
        INSERT INTO users (username, email, password, isadmin)
        VALUES (?, ?, ?, ?)
        '''
        if data.execute(query, (username, email, hashed_password, admin)) == True :
            return True
        else:
            return False





def loginU(username_email,password):
    hashed_password = hash_password(password)
    query = '''
    SELECT userid, username, email, isadmin FROM users
    WHERE (username = ? OR email = ?) AND password = ?
    '''
    with createDBconnection() as conn:
        data = conn.cursor()  # Use a different variable name for the cursor
        data.execute(query, (username_email, username_email, hashed_password))
        result = data.fetchone()
        return result


def UserOrEmailExist(username, email):
    with createDBconnection() as conn:
        data = conn.cursor()

        # Check if the given username or email exists in the users table
        query = '''
        SELECT COUNT(*) FROM users WHERE username = ? OR email = ?
        '''
        data.execute(query, (username, email))
        count = data.fetchone()[0]

        if count > 0:
            return True
        else:
            return False
        


def update_user_token(userid, token):
    with createDBconnection() as conn:
        data = conn.cursor()

        # Update the user's token in the users table
        query = '''
        UPDATE users SET token = ? WHERE userid = ?
        '''
        data.execute(query, (token, userid))
        
        conn.commit()


def delete_user_token(userid):
    with createDBconnection() as conn:
        data = conn.cursor()
        query = '''
        UPDATE users SET token = NULL WHERE userid = ?
        '''
        data.execute(query, (userid,))
        conn.commit()


def admin_update_user(username, email, isadmin, id):
    with createDBconnection() as conn:
        data=conn.cursor()
        query = '''
        UPDATE users SET username = ?, email = ?, isadmin = ? WHERE userid = ?        
        '''
        data.execute(query,(username, email, isadmin,id))
        conn.commit()


def check_id_exist(id):
    with createDBconnection() as conn:
        data = conn.cursor()
        query='''
        SELECT COUNT(*) FROM users WHERE userid = ?
        '''
        data.execute(query,(id,))
        count = data.fetchone()[0]

        if count > 0:
            return True
        else:
            return False
        
def admin_delete_user(id):
    with createDBconnection() as conn:
        data = conn.cursor()
        query='''
        DELETE FROM users WHERE userid = ?
        '''
        data.execute(query,(id,))


def get_all_users():
    with createDBconnection() as conn:
        data = conn.cursor()
        query = '''SELECT userid, username, email, isadmin FROM users'''
        data.execute(query)
        users = data.fetchall()
        return users
    


def get_user_by_id(userid):
    with createDBconnection() as conn:
        data = conn.cursor()
        query = '''SELECT userid, username, email, photo FROM users WHERE userid = ?'''
        data.execute(query, (userid,))
        user = data.fetchone()
        return user
    
    
def User_edit_profile(username, email, id):
    with createDBconnection() as conn:
        data = conn.cursor()
        query = '''
        UPDATE users SET username = ?, email = ? WHERE userid = ?
        '''
        data.execute(query, (username, email, id))
        conn.commit()


def update_photo(photo,id):
    with createDBconnection() as conn:
        data = conn.cursor()
        query = '''
        UPDATE users SET photo = ? WHERE userid = ?
        '''
        data.execute(query, (photo, id))
        conn.commit()


def update_pw(password,id):
    with createDBconnection() as conn:
        hashed = hash_password(password)
        data = conn.cursor()
        query = '''
        UPDATE users SET password = ? WHERE userid = ?
        '''
        data.execute(query, (hashed, id))
        conn.commit()
















ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def secure_filename_and_extension(filename):
    filename = secure_filename(filename)
    filename, extension = os.path.splitext(filename)
    return filename, extension.lstrip('.')

MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB

def is_valid_file(file):
    return file and allowed_file(file.filename) and len(file.read()) <= MAX_FILE_SIZE







def add_film(filmname, genre, price, availabletickets, photo):
    with createDBconnection() as conn:
        data = conn.cursor()
        
        query = '''
        INSERT INTO films (filmname, genre, price, availabletickets, photo)
        VALUES (?, ?, ?, ?, ?)
        '''
        data.execute(query,(filmname, genre, price, availabletickets, photo))
        conn.commit()


def get_all_films():
    with createDBconnection() as conn:
        data = conn.cursor()
        query = '''SELECT filmname, genre, price, availabletickets, photo FROM films'''
        data.execute(query)
        films = data.fetchall()
        return films

def get_film_by_name(filmname):
    with createDBconnection() as conn:
        data = conn.cursor()
        query = '''SELECT filmname, genre, photo, price, availabletickets FROM films WHERE filmname = ?'''
        data.execute(query, (filmname,))
        film = data.fetchone()
        return film
    
def check_if_film_exists(filmname):
    with createDBconnection() as conn:
        data = conn.cursor()
        query = "SELECT COUNT(*) FROM films WHERE filmname = ?"
        data.execute(query, (filmname,))
        count = data.fetchone()[0]
        return count > 0


def get_filmdetails_byName(filmname):
    with createDBconnection() as conn:
        data = conn.cursor()
        query = '''SELECT * FROM films WHERE filmname = ?'''
        data.execute(query, (filmname,))
        film = data.fetchone()
        return film
    





def get_comments_for_film(filmname):
    with createDBconnection() as conn:
        data = conn.cursor()
        query = '''SELECT * FROM comments WHERE filmname = ?'''
        data.execute(query,(filmname,))
        film = data.fetchall()
        return film
    

def update_available_tickets(newavailabletickets,filmname):
    with createDBconnection() as conn:
        data = conn.cursor()
        query = '''UPDATE films SET availabletickets = ? WHERE filmname = ?'''
        data.execute(query,(newavailabletickets,filmname))
        conn.commit()


def update_soldout(soldout,filmname):
    with createDBconnection() as conn:
        data = conn.cursor()
        query = '''UPDATE films SET soldout = ? WHERE filmname = ?'''
        data.execute(query,(soldout,filmname))
        conn.commit()


def get_price_by_filmname(filmname):
    with createDBconnection() as conn:
        data = conn.cursor()
        query = '''SELECT price FROM films WHERE filmname = ?'''
        data.execute(query, (filmname,))
        price = data.fetchone()
        return price[0] if price else None
    




def delete_film(filmname):
    with createDBconnection() as conn:
        data = conn.cursor()
        query = '''DELETE FROM films WHERE filmname = ?'''
        data.execute(query, (filmname,))
        conn.commit()


def update_tickets(availabletickets,filmname):
    with createDBconnection() as conn:
        data = conn.cursor()
        query = '''UPDATE films SET availabletickets = ?, soldout = 0 WHERE filmname = ?'''
        data.execute(query,(availabletickets,filmname))
        conn.commit()



def get_comments(filmname):
    with createDBconnection() as conn:
        data = conn.cursor()
        query = '''SELECT * FROM comments WHERE filmname = ?'''
        data.execute(query,(filmname,))
        comment = data.fetchall()
        return comment
    

def add_comment(userid,comment,filmname,username,userphoto):
    with createDBconnection() as conn:
        data = conn.cursor()
        query = '''INSERT INTO comments (userid, comment, filmname, username, userphoto)
        VALUES (?, ?, ?, ?, ?)'''
        data.execute(query,(userid,comment,filmname,username,userphoto))
        conn.commit()