from flask import Flask, app ,jsonify,g, render_template , request  , redirect, url_for, session,flash,abort,render_template_string
import sqlite3
from database import *
import secrets
import re
from werkzeug.utils import secure_filename
import base64
import os
import time



cinema=Flask(__name__)
cinema.secret_key = secrets.token_urlsafe(32)
connection = createDBconnection()


cinema.config['UPLOAD_FOLDER'] = 'static/images'

def is_non_negative(value):
    return value >= 0

def check_admin_input(input_string):
    pattern = r'^(0|1)$'
    return re.match(pattern, input_string) is not None

def is_valid_password(password):
    pattern = r'^(?=.*[0-9])(?=.*[!@#$%^&*])(?=.*[a-z])(?=.*[A-Z]).{8,20}$'
    return bool(re.match(pattern, password))

def check_auth():
    # List of routes that don't require authentication
    whitelist = ['login', 'register']

    # If the route is not in the whitelist and no valid token is found /profile session['token']
    if request.endpoint not in whitelist and 'token' not in session:
        return False
    else:
        return True

@cinema.route("/")
def main():
    return redirect(url_for('films'))



@cinema.route("/films")
def films():
    if check_auth() == False:
        return redirect(url_for("login")), 302
    else:
        films_data = get_all_films()
        search_param = request.args.get("search")
        
        if search_param and search_param.strip() != "":
            # Filter films based on an exact match of the film name
            films_data = [film for film in films_data if search_param.lower() == film[0].lower()]
        
        return render_template("films.html", films_data=films_data, search_param=search_param,id=session['userid'])



@cinema.route("/films/<filmname>")
def viewfilm(filmname):
    
    if check_auth() == False:
        return redirect(url_for("login")), 302
    else:
        film_data = get_filmdetails_byName(filmname)
        if film_data :
            film_comments = get_comments(filmname)
            return render_template("film_details.html",film_data=film_data, film_comments = film_comments, current_user=session.get('userid')) ,302
        else:
            return render_template_string("Film Not Found") , 404


@cinema.route("/add_comment/<filmname>" , methods=['POST','GET'])
def addcomment(filmname):
    if check_auth() == False:
        return redirect(url_for("login")), 302
    else:
        if request.method == 'GET':
            return render_template("film_details.html" ,film_data = film_data,film_comments = film_comments,current_user=session.get('userid')), 200
        elif request.method == 'POST':
            film_comments = get_comments(filmname)
            film_data = get_filmdetails_byName(filmname)
            user_data = get_user_by_id(session['userid'])
            comment = request.form.get('comment_text')
            username = user_data[1]
            user_photo = user_data[3]
            userid=user_data[0]
        
            if comment:
                add_comment(userid,comment,filmname,username,user_photo)
                return render_template("film_details.html" ,film_data = film_data,film_comments = film_comments,current_user=session.get('userid'))
            else:
                return render_template_string(f"<script>setTimeout(function () {{window.location.href = '/films/{filmname}';}}, 2000); </script><h1>Enter Comment</h1>"),304
        
        else:
            return render_template_string("<h1>Method Not Allowed</h1>"), 405


@cinema.route("/buy_tickets/<filmname>" ,methods=['POST'])
def buy_ticket(filmname):
        
    if check_auth() == False:
        return redirect(url_for("login")), 302
    else:

        if request.method == 'POST':
            film_data = get_filmdetails_byName(filmname)
            price = request.form.get('price')
            realPrice = film_data[4]
            availabletickets = film_data[5]
            soldout = film_data[6]
            tickets = int(request.form.get('ticket_quantity'))  # Convert to int ("<script>setTimeout(function () {window.location.href = '/admin/user/edit';}, 2000); </script><h1>User ID doesn't exist</h1>")
            

            
            if film_data:
                if availabletickets != 0:
                    if tickets >= 1 and tickets <= availabletickets:
                        if float(price) == realPrice and is_non_negative(float(price)) :
                            newtickets = availabletickets - tickets
                            update_available_tickets(newtickets, film_data[1])
                            return render_template_string(f"<h1 style='color:green'>you have purchased {tickets} tickets for {filmname}, Total = {float(price) * tickets}</h1><script>setTimeout(function () {{window.location.href = '/films/{filmname}';}}, 2000);</script>")
                        else:
                            return render_template("forbiddenIDOR.html")
                    else:
                        return render_template_string(f"<script>setTimeout(function () {{window.location.href = '/films/{filmname}';}}, 2000); </script><h1 style='color:red'>Don't purchase more than available tickets or less than 1</h1>") , 403
                elif availabletickets == 0:
                    soldout = 1
                    update_soldout(soldout, film_data[1])
                    return render_template(f"/films/{film_data[1]}")
            else:
                render_template_string(f"<script>setTimeout(function () {{window.location.href = '/films';}}, 2000); </script>Film Not Found"), 200
        else:
            render_template_string(f"<script>setTimeout(function () {{window.location.href = '/films';}}, 2000); </script><h1 style='color:red'>Method Not Allowed</h1>") , 405



@cinema.route("/profile/<id>", methods=['GET'])
def profile(id):
    realID = int(session['userid'])
    if int(id) == session['userid']:
        if request.method == "GET":
            user_data = get_user_by_id(realID)
            return render_template("profile.html",user_data=user_data, id=realID)
        else:
            return render_template_string("<h1>Method Not Allowed</h1>"), 405
    else:
        return render_template("forbiddenIDOR.html") , 403


@cinema.route("/profile/<id>/uploadphoto" ,methods=['POST'])
def uploadphoto(id):
    if check_auth() == False:
        return redirect(url_for("login")), 302
    else:
        realID = int(session['userid'])
        if int(id) == session['userid']:
            if request.method == "POST":

                user_data = get_user_by_id(realID)

                photo = request.files["photo"]
                if photo and is_valid_file(photo):
                    filename, extension = secure_filename_and_extension(photo.filename)
                    file_path = os.path.join(cinema.config['UPLOAD_FOLDER'], f"{filename}.{extension}") 
                    
                    photo.seek(0)
                    photo.save(file_path)
                    update_photo(f"{filename}.{extension}",realID)
                    if user_data[3] != 'default.png':
                        os.remove(os.path.join(cinema.config['UPLOAD_FOLDER'], user_data[3]))

                    return redirect(url_for('profile', id=realID)) ,302
                else:
                    return render_template_string("File not allowed") , 403
            else:
                return render_template_string("<h1>Method Not Allowed</h1>"), 405
        else:
            return render_template("forbiddenIDOR.html") , 403
    


@cinema.route("/profile/<id>/updateusernameemail" , methods=['POST'])
def updateusernameemail(id):
    if check_auth() == False:
        return redirect(url_for("login")), 302
    else:
        realID = int(session['userid'])
        if int(id) == session['userid']:
            if request.method == "POST":
                username = request.form.get('username')
                email = request.form.get('email')
                if username and email:
                    if UserOrEmailExist(username,email) == False:
                        User_edit_profile(username,email,realID)
                        return redirect(url_for('profile', id=realID)) ,302
                    else:
                        return render_template_string("credentials exist"), 403
                else:
                    return render_template_string("Please, fill the inputs"), 403
            else:
                return render_template_string("<h1>Method Not Allowed</h1>"), 405
        else:
            return render_template("forbiddenIDOR.html") , 403


@cinema.route("/profile/<id>/updatepw",methods=['POST'])
def updatepw(id):
    if check_auth() == False:
        return redirect(url_for("login")), 302
    else:
        realID = int(session['userid'])
        if int(id) == session['userid']:
            if request.method == "POST":
                password = request.form.get('password')
                if is_valid_password(password) and password :
                    update_pw(password,realID)
                    return redirect(url_for('profile', id=realID)) ,302
                else:
                    return render_template_string("<h1>8-20 char, 1[symbol,UPPERCASE,lowercase,number]</h1>") , 403
            else:
                return render_template_string("<h1>Method Not Allowed</h1>"), 405
        else:
            return render_template("forbiddenIDOR.html") , 403

@cinema.route("/login" ,methods=['GET','POST'])
def login():
    
    if request.method == 'GET':
        return render_template('login.html')
    elif request.method == 'POST':
        result = loginU(request.form.get('username_email'),request.form.get('password'))
        if result:
            token = generate_token()
            session['token'] = token
            session['userid'] = int(result[0])
            update_user_token(int(result[0]), token)   #result0 = 'userid'
            if int(result[3]) != 1:
                return redirect(url_for('films'))
            else:
                session['isadmin'] = int(result[3])
                return redirect(url_for('admin'))
        else:
            flash('failed login','error')
            return render_template('login.html')
        

@cinema.route("/register" ,methods=['GET','POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    elif request.method == 'POST':
        if is_valid_password(request.form.get('password')):
            if UserOrEmailExist(request.form.get('username'), request.form.get('email')):
                return render_template('forbidden.html'), 403
            else:
                if registerU(request.form.get('username'), request.form.get('email'), request.form.get('password'))==True:
                    return render_template('login.html'), 302
                else:
                    # Handle unsuccessful registration here
                    error_message = "Registration failed. Please try again."
                    return render_template('register.html', error=error_message)
        else:
            flash('8-20 char, 1[symbol,UPPERCASE,lowercase,number]',category='error')
            return render_template("register.html")
        


@cinema.route("/logout")
def logout():
    id=int(session['userid'])
    if not id:
        redirect(url_for('login'))
    delete_user_token(id)
    session.clear()
    session.pop('token', None)
    return redirect(url_for('login')) 


@cinema.route("/admin")
def admin():
    if 'isadmin' not in session :
        return render_template_string("<h1 style="'color:red'">403 Not Authorized</h1>"), 403
    else:
        return render_template("admin.html")

@cinema.route("/admin/user/<action>" ,methods=['GET','POST'])
def actionToUsers(action):
    if action == 'add':
        if 'isadmin' in session:
            if request.method == 'GET':
                return render_template("adduser.html")
            elif request.method == 'POST':
                if is_valid_password(request.form.get('password')) and check_admin_input(request.form.get('admin')):
                    if UserOrEmailExist(request.form.get('username'), request.form.get('email')):
                        return render_template('forbidden.html'), 403
                    else:
                        if registerUA(request.form.get('username'), request.form.get('email'), request.form.get('password'), request.form.get('admin')):
                            return render_template('admin.html'), 302
                        else:
                            # Handle unsuccessful registration here
                            return render_template('adduser.html')
                else:
                    flash('Error : Follow PW Rules OR specify valid admin number', category='error')
                    return render_template("adduser.html")
            else:
                return render_template_string("<h1>Method Not Allowed</h1>"), 405
        else:
            return render_template('forbidden.html'), 403
    
    elif action == 'edit' :
        if 'isadmin' in session:
            if request.method == 'GET':
                return render_template("edituser.html")
            elif request.method == 'POST' :
                if is_non_negative(int(request.form.get('id'))) and (request.form.get('id')).isnumeric():
                    if check_id_exist(request.form.get('id')):
                        if check_admin_input(request.form.get('admin')) :
                            admin_update_user(request.form.get('username'), request.form.get('email'),request.form.get('admin'),request.form.get('id'))
                            return render_template("edituser.html")
                        else:
                            flash('Error : specify valid admin number', category='error')
                            return render_template("edituser.html")
                    else:
                        return render_template_string("<script>setTimeout(function () {window.location.href = '/admin/user/edit';}, 2000); </script><h1>User ID doesn't exist</h1>")
                else:
                    flash('Error : specify valid id', category='error')
                    return render_template("edituser.html")
                
            else:
                    return render_template_string("<h1>Method Not Allowed</h1>"), 405
        else:
                return render_template('forbidden.html'), 403
        
    elif action == 'delete':
        if 'isadmin' in session:
            if request.method == 'GET':
                return render_template("deleteuser.html")
            elif request.method == 'POST':
                if is_non_negative(int(request.form.get('id'))) and request.form.get('id').isnumeric():
                    if check_id_exist(request.form.get('id')):
                        admin_delete_user(request.form.get('id'))
                        return render_template("deleteuser.html"), 200
                    else:
                        return render_template_string("<script>setTimeout(function () {window.location.href = '/admin/user/delete';}, 2000); </script><h1>User ID doesn't exist</h1>")
                else:
                    flash("put !negative num Value",category="error")
                    return render_template("deleteuser.html")
            else:
                return render_template_string("<h1>Method Not Allowed</h1>"), 405
        else:
            return render_template('forbidden.html'), 403
        
    elif action == 'view':
        if 'isadmin' in session:
            if request.method == 'GET':
                all_users = get_all_users()
                return render_template("viewusers.html", users=all_users)
            else:
                return render_template_string("<h1>Method Not Allowed</h1>"), 405
        else:
            return render_template('forbidden.html'), 403
    else:
        return render_template_string("<h1>File not Found</h1>"), 404

@cinema.route("/admin/film/<action>" ,methods=['GET','POST'])
def actionToFilm(action):
    if action == 'add':
        if 'isadmin' in session:
            if request.method == 'GET':
                return render_template("addfilm.html")
            elif request.method == 'POST':
                filmname = request.form.get('filmname')
                genre = request.form.get('genre')
                price = int(request.form.get('price'))
                availabletickets = int(request.form.get('availabletickets'))
                photo = request.files['photo']

                

                if photo and allowed_file(photo.filename):
                    filename, extension = secure_filename_and_extension(photo.filename)
                    file_path = os.path.join(cinema.config['UPLOAD_FOLDER'], f"{filename}.{extension}") #/static/images/filmname.extension
                    
                    if is_valid_file(photo):
                        photo.seek(0)
                        photo.save(file_path)
                        add_film(filmname, genre, price, availabletickets, f"{filename}.{extension}")
                        return render_template_string("<script>setTimeout(function () {window.location.href = '/admin/film/add';}, 2000); </script><h2 style='color:green'>Film Added Succcessfuly </h2>"), 200
                    else:
                        return render_template_string("<script>setTimeout(function () {window.location.href = '/admin/film/add';}, 2000); </script><h1 style='color:red'>invalid image file</h1>"), 403
                else:
                    return render_template_string("<script>setTimeout(function () {window.location.href = '/admin/film/add';}, 2000); </script><h1 style='color:red'>invalid format</h1>"), 403
            else:
                return render_template_string("<h1>Method Not Allowed</h1>"), 405
        else:
            return render_template('forbidden.html'), 403
    elif action == "delete":
        if 'isadmin' in session:
            if request.method == 'GET':
                return render_template("deletefilm.html")
            elif request.method == 'POST':
                filmname = request.form.get('filmname')
                if get_film_by_name(filmname):
                    delete_film(filmname)

                    return render_template("deletefilm.html")
                else:
                    return render_template_string("<script>setTimeout(function () {window.location.href = '/admin/film/delete';}, 2000); </script><h1 style='color:red'>Film Not Found</h1>"), 403
            else:
                return render_template_string("<h1>Method Not Allowed</h1>"), 405
        else:
            return render_template('forbidden.html'), 403
    elif action == "addtickets":
        if 'isadmin' in session:
            if request.method == 'GET':
                return render_template("addtickets.html")
            elif request.method == 'POST':
                filmname = request.form.get('filmname')
                availabletickets = int(request.form.get('availabletickets'))
                if get_film_by_name(filmname):
                    update_tickets(availabletickets,filmname)
                    return render_template("addtickets.html")
                else:
                    return render_template_string("<script>setTimeout(function () {window.location.href = '/admin/film/addtickets';}, 2000); </script><h1 style='color:red'>Film Not Found</h1>"), 403
            else:
                return render_template_string("<h1>Method Not Allowed</h1>"), 405
        else:
            return render_template('forbidden.html'), 403
    else:
        return render_template_string("<h1>File not Found</h1>"), 404




###########################################
if __name__ == "__main__":
    init_db(connection)
    cinema.run(debug=True, port=3000)