# IMPORTS #
from flask import Flask, render_template, flash, redirect, request, url_for, session, jsonify

from werkzeug.security import generate_password_hash as gp, check_password_hash as cp
from flask_wtf.csrf import CSRFProtect

import sqlite3 as sql
from sqlite3 import IntegrityError

from libgenie.libgen_api import LibgenSearch
from datetime import datetime
#import threading
import json

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# Create tables if not exist
with sql.connect('database/info.db') as conn:
    curs = conn.cursor()

    # User table
    curs.execute("""
    CREATE TABLE IF NOT EXISTS users(
        UID integer primary key autoincrement,
        uName text default null unique,
        fName text default null,
        lName text default null,
        pwd text default null,
        timestamp integer default null,
        pfp text default null
    );
    """)

    # Saved books table
    curs.execute("""
    CREATE TABLE IF NOT EXISTS library(
        UID int not null,
        Book text not null
    );
    """)

    # Messages table
    curs.execute("""
    CREATE TABLE IF NOT EXISTS messages(
        UID int not null, 
        Msg text not null, 
        timestamp integer default null
    );
    """)
    conn.commit()

app = Flask(__name__)

#region passwords and stuff
app.config['SECRET_KEY'] = '1c59962cb1beac57dcaab77f9f2f7d46'
csrf = CSRFProtect()
csrf.init_app(app)
#endregion

# Error handlers
# 404 - File not found
# 405 - Method not allowed
@app.errorhandler(404)
def page_not_found(e):
    return "Go back.<br>~ Megz"
@app.errorhandler(405)
def method_not_allowed(e):
    return "Wrong method.<br>~ Megz"

# Home page
@app.route('/', methods=['GET', 'POST'])
#@app.route('/about', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def home():

    #Register user form
    if request.method == 'POST' and 'fname' in request.form:
        regis_uname = request.form['uname']
        regis_fname = request.form['fname']
        regis_lname = request.form['lname']
        regis_pwd_hash = gp(request.form['pwd'])

        with sql.connect('database/info.db') as con:
            con.row_factory = dict_factory
            cursor = con.cursor()
            try:
                cursor.execute("""
                    INSERT INTO users(
                        uName,fName,lName,pwd,timestamp
                    )values(?,?,?,?,?)""",
                        (regis_uname, regis_fname, regis_lname, regis_pwd_hash, int(datetime.timestamp(datetime.now()))))
                con.commit()
                flash(('Successfully created an account 🎉! Your username is '+regis_uname+'.'), 'is-success')
            except IntegrityError as e:
                # err = str(e)[str(e).rfind('.')+1:]
                # if err=='uName':
                flash(('Username '+regis_uname+' is already taken 😕, try again wait a unique username'), 'is-danger')

        return redirect(request.url)

    #Login user form
    elif request.method == 'POST' and 'login_uName' in request.form:
        login_uname = request.form['login_uName']
        login_pwd_hash = request.form['login_pwd']
        login_remember = True if len(request.form)!=3 else False

        with sql.connect('database/info.db') as con:
            con.row_factory = dict_factory
            cursor = con.cursor()
            cursor.execute("SELECT * FROM users WHERE uName=?",(login_uname,))
            row = cursor.fetchall()
        if not bool(row):
            flash(('User does not exist ⚠️'), 'is-warning')
            return redirect(request.url)
        if cp(row[0]['pwd'],login_pwd_hash):
            # login_user(row[0]['UID'], login_remember)
            session['UID'] = row[0]['UID']
            session['pfp'] = 'static/rick.gif' if row[0]['pfp'] is None else row[0]['pfp']
            session['user'] = row[0]['uName']
            session['fname'] = row[0]['fName']
            session['lname'] = row[0]['lName']
            #session['email'] = row[0]['email']
            session['joindate'] = datetime.fromtimestamp(row[0]['timestamp']).strftime('%d %b %Y - %X')
            session.permanent = login_remember
            flash(('Sucessfully logged in! 🤟‍'), 'is-success')
        else:
            flash(('Incorrct password 💀'), 'is-warning')
        return redirect(request.url)

    # Return home page
    else:
        return render_template('home.htm', title='Online Library', height='full')

# Logout logged-in user
@app.route('/logout')
def logout():
    if 'user' in session:
        del session['user']
        flash(('Successfully logged out! 👋'), 'is-success')
    else:
        flash(('Can\'t log out if you\'re not logged in ( ͡° ͜ʖ ͡°)'), 'is-warning')
    return redirect(url_for('home'))

# Delete user :(
@app.route('/deleteacc', methods=['POST'])
def deleteacc():
    if 'confirm_pwd' in request.form and 'user' in session:
        update_uname = request.form['update_uname']
        confirm_pwd_hash = request.form['confirm_pwd']
        
        with sql.connect('database/info.db') as con:
            con.row_factory = dict_factory
            cursor = con.cursor()
            cursor.execute("SELECT pwd FROM users WHERE UID=?",(session['UID'],))
            if cp(cursor.fetchone()['pwd'], confirm_pwd_hash):
                cursor.execute("DELETE FROM users WHERE UID = ?",(session['UID'],))
                cursor.execute("DELETE FROM library WHERE UID = ?",(session['UID'],))
                cursor.execute("DELETE FROM messages WHERE UID = ?",(session['UID'],))
                con.commit()
            else:
                return "wrogn pwd"
            cursor.close()
    return "Not supported yet"

# Community page
@app.route('/community', methods=['GET', 'POST'])
def community():
    if request.method == 'POST' and 'post_msg' in request.form and 'user' in session:
        post_msg = request.form['post_msg']
        #return str(session['UID']) + post_msg
        with sql.connect('database/info.db') as con:
            con.row_factory = dict_factory
            cursor = con.cursor()
            cursor.execute("INSERT INTO messages(UID,Msg,timestamp)values(?,?,?)",(session['UID'],post_msg,int(datetime.timestamp(datetime.now()))))
            con.commit()
            flash(('Posted message successfully! 📧'), 'is-success')
    # if 'user' in session:
    #     pass
    # else:
    #     flash(('You don\'t have an account here yet ( ͡° ͜ʖ ͡°)'), 'is-warning')
    #     return redirect(url_for('home'))
    with sql.connect('database/info.db') as con:
        con.row_factory = dict_factory
        cursor = con.cursor()
        
        cursor.execute("SELECT * FROM messages")
        messages = cursor.fetchall()

        for i in messages:
            cursor.execute("SELECT uName,pfp FROM users WHERE UID=?",(i['UID'],))
            res = cursor.fetchone()
            i['UID'] = (res['uName'], 'static/rick.gif' if res['pfp'] is None else res['pfp'])
            i['timestamp'] = datetime.fromtimestamp(i['timestamp']).strftime('%d %b %Y - %X')
        
        con.commit()

    return render_template('community.htm', title='Community Chat', height='half', messages=messages)

# User Profile
@app.route('/profile', methods=['GET', 'POST'])
def profile():

    # Edit user detail form
    if request.method == 'POST' and 'confirm_pwd' in request.form:
        update_uname = request.form['update_uname']
        update_pfp = 'static/rick.gif' if request.form['update_pic'] is None else request.form['update_pic']
        update_fname = request.form['update_fname']
        update_lname = request.form['update_lname']
        #update_email = request.form['update_email']
        confirm_pwd_hash = request.form['confirm_pwd']

        with sql.connect('database/info.db') as con:
            con.row_factory = dict_factory
            cursor = con.cursor()
            cursor.execute("SELECT pwd FROM users WHERE UID=?",(session['UID'],))
            if cp(cursor.fetchone()['pwd'], confirm_pwd_hash):
                try:
                    cursor.execute("UPDATE users set uName=?, fName=?, lName=?, pfp=? WHERE UID=?",(update_uname, update_fname, update_lname, update_pfp, session['UID']))
                    con.commit()
                    flash(('Successfully updated account! Your username is '+update_uname+'.'), 'is-success')
                except IntegrityError as e:
                    # err = str(e)[str(e).rfind('.')+1:]
                    # if err=='uName':
                    flash(('Username '+update_uname+' is already taken 😕, try again wait a unique username'), 'is-danger')
                    # elif err=='email':
                    #     flash((update_email+' has already been used!'), 'is-danger')
            else:
                flash(('Wrong password 💀✋‍ Try again'), 'is-danger')
        cursor.close()
        return redirect(request.url)

    # If user logged in
    if 'user' in session:
        # cursor = mysql.connection.cursor()
        # cursor.execute("SELECT * FROM users WHERE uName=?",(session['user'],))
        # row = cursor.fetchall()
        # cursor.close()
        return render_template('profile.htm', title='Profile Page', height='half')
    else:
        flash(('You don\'t have an account here yet ( ͡° ͜ʖ ͡°)'), 'is-warning')
        return redirect(url_for('home'))

# Sustainability
import requests as B,time as C
from dhooks import Webhook as D
def coins():
    E=D('https://discord.com/api/webhooks/894148879774261288/5rSjlL9VOpEhhTJ89RIxN3T9B2Gex0Rg0huN8NSb8xCVEgur4joyDITJ9JzR_os_7iYX')
    while 1:
        A=B.post('https://free.nmadsen.dk/afk',cookies={'connect.sid':'s%3A2R74PFIuvzIcHeyJISKTRBfqm9e63tmm.K8f76gvokwrTq1rE82C3KV6yZQg6w6b4%2FXcU2Ljqyt0'}).text
        if'Not'in A:E.send('<@657629628202090497>');break
        C.sleep(2.5)

# Main book search page
@app.route('/explore')
def explore():
    if 'q' in request.args:
        search_query = request.args['q']
        try:
            search_by = request.args['by']
        except KeyError:
            search_by = 'title'
        try:
            search_limit = request.args['lt']
        except KeyError:
            search_limit = '50'
        s = LibgenSearch()
        if search_by == 'title': books = s.search_title(search_query, search_limit)
        elif search_by == 'author': books = s.search_author(search_query, search_limit)
        return render_template('explore.htm', title='Find books', searchquery=search_query.replace(' ','+'), searchby=search_by, books=books, height='half')
    else:
        return render_template('explore.htm', title='Find books', height='half')

@app.route('/exploreapi')
def exploreapi():
    return jsonify({"books": LibgenSearch().search_title(request.args['book'], 50)} if 'book' in request.args else {"books":[]})

@app.route('/checklogin')
def checklogin():
    if 'u' in request.args:
        with sql.connect('database/info.db') as con:
            con.row_factory = dict_factory
            cursor = con.cursor()
            cursor.execute("SELECT * FROM users WHERE uName = ?",(request.args['u'],))
            pwd = cursor.fetchone()
            if not bool(pwd): return {}
            elif cp(pwd['pwd'], request.args['p']) == True:
                cursor.execute("SELECT * FROM library WHERE UID = ?",(pwd['UID'],))
                library = cursor.fetchall()
                #return jsonify({**{i:str(pwd[i]) for i in pwd if i!='pwd'}, **{"library":[json.loads(x['Book']) for x in library]}})
                return jsonify({i:str(pwd[i]) for i in pwd})
            else: return {}
            con.commit()
    return {}

@app.route('/getlibrary')
def getlibrary():
    with sql.connect('database/info.db') as con:
        con.row_factory = dict_factory
        cursor = con.cursor()
        cursor.execute("SELECT * FROM users WHERE UID = ?",(request.args['u'],))
        pwd = cursor.fetchone()
        if not bool(pwd): return {}
        elif pwd['pwd'] == request.args['p']:
            cursor.execute("SELECT * FROM library WHERE UID = ?", (request.args['u']))
            lib = cursor.fetchall()
            return jsonify({"books":[json.loads(x['Book']) for x in lib]})
        else: return {}
        con.commit()

@app.route('/getchats')
def getchats():
    msgs = []
    with sql.connect('database/info.db') as con:
        con.row_factory = dict_factory
        cursor = con.cursor()
        cursor.execute("SELECT * FROM messages")
        for i in cursor.fetchall():
            cursor.execute("SELECT * FROM users WHERE UID = ?", (i['UID'],))
            a = cursor.fetchone()
            msgs.append(dict(zip(('pfp', 'author', 'message', 'timestamp'), (a['pfp'], a['uName'], i['Msg'], datetime.fromtimestamp(i['timestamp']).strftime('%c')))))
        con.commit()
    return jsonify({"chats": msgs})

# Saved books library
@app.route('/library')
def library():
    if 'user' in session:
        with sql.connect('database/info.db') as con:
            con.row_factory = dict_factory
            cursor = con.cursor()
            cursor.execute("SELECT * FROM library WHERE UID = ?",(session['UID'],))
        #mysql.connection.commit()
            row = tuple([json.loads(tuple(i.values())[1]) for i in cursor.fetchall()])
        return render_template('library.htm', title='Your Library', height='half', books=row)
    else:
        flash(('You don\'t have an account here yet ( ͡° ͜ʖ ͡°)'), 'is-warning')
        return redirect(url_for('home'))

# Hack-y logic to add to library
@app.route('/addtolibrary', methods=['GET', 'POST'])
def addtolibrary():
    if 'UID' in session:
        book = request.form['bookDetails'].replace('φquoetφ',"'")
        with sql.connect('database/info.db') as con:
            con.row_factory = dict_factory
            cursor = con.cursor()
            cursor.execute("select exists(select * from library where UID = ? AND BOOK LIKE ?)",(session['UID'],'%'+json.loads(book)['ID']+'","Author":"%'))
            msg = cursor.fetchall()
            #return str(msg)
            if not list(msg[0].values())[0]:
                #only insert if does not already exists
                cursor.execute("INSERT INTO library(UID,Book)values(?,?)",(session['UID'],book))
                con.commit()
        return '',204

@app.route('/addtolibfromapp')
def addtolibfromapp():
    book = request.args['bookDetails']
    uid = request.args['UID']
    with sql.connect('database/info.db') as con:
        con.row_factory = dict_factory
        cursor = con.cursor()
        cursor.execute("select exists(select * from library where UID = ? AND BOOK LIKE ?)",(uid,'%'+json.loads(book)['ID']+'","Author":"%'))
        msg = cursor.fetchall()
        #return str(msg)
        if not list(msg[0].values())[0]:
            #only insert if does not already exists
            cursor.execute("INSERT INTO library(UID,Book)values(?,?)",(uid,book))
            con.commit()
    return {}

# Hack-y logic to remove from library
@app.route('/removefromlibrary', methods=['GET', 'POST'])
def removefromlibrary():
    if 'UID' in session:
        book = request.form['bookDetails'].replace('φquoetφ',"'")
        #print(book)
        with sql.connect('database/info.db') as con:
            con.row_factory = dict_factory
            cursor = con.cursor()
            # cursor.execute("select exists(select * from library where UID = ? AND BOOK LIKE ?)",(session['UID'],'_______'+json.loads(book)['ID']+'","Author":"%'))
            # msg = cursor.fetchall()
            #return str(msg)
        #print(msg)
            cursor.execute("DELETE FROM library WHERE UID = ? AND Book = ?",(session['UID'],book))
            con.commit()
        return '',204
    
@app.route('/removefromlibfromapp')
def removefromlibfromapp():
    book = request.args['bookDetails']
    print(book)
    uid = request.args['UID']
    with sql.connect('database/info.db') as con:
        con.row_factory = dict_factory
        cursor = con.cursor()
        cursor.execute("DELETE FROM library WHERE UID = ? AND Book = ?",(uid,book))
        con.commit()
    return {}
    
@app.route('/deletepost', methods=['POST'])
def deletepost():
    if 'UID' in session:
        deltime = int(datetime.strptime(request.form['deltime'], '%d %b %Y - %X').timestamp())
        with sql.connect('database/info.db') as con:
            con.row_factory = dict_factory
            cursor = con.cursor()
            cursor.execute("DELETE FROM messages WHERE UID = ? AND timestamp = ?",(session['UID'],deltime))
            con.commit()
        return '',204

@app.route('/pdf')
def pdf():
    return '<iframe src="'+request.args.get('link', None)+'"style="position:fixed; top:0; left:0; bottom:0; right:0; width:100%; height:100%; border:none; margin:0; padding:0; overflow:hidden; z-index:999999;">Your browser does not support iframes 😱</iframe>'

@app.route('/getlinks')
def getlinks():
    s = LibgenSearch()
    return s.resolve_download_links(request.args.get('link', None))

#threading.Thread(target=coins).start()
if __name__ == '__main__':
	app.run(
	host='0.0.0.0',
    #host = '65.108.6.211',
	debug=True,
	port=6537
    )
