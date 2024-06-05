from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL 설정
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'your_mysql_user'
app.config['MYSQL_PASSWORD'] = 'your_mysql_password'
app.config['MYSQL_DB'] = 'your_database_name'

mysql = MySQL(app)

@app.route('/')
def index():
     return render_template('home_ver2.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'userid' in request.form and 'password' in request.form:
        userid = request.form['userid']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE userid = %s AND password = %s', (userid, password,))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            return redirect(url_for('calendar'))
        else:
            msg = 'Incorrect userid/password!'
    return render_template('login.html', msg=msg)

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form and 'userid' in request.form and 'phone_number' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        userid = request.form['userid']
        phone_number = request.form['phone_number']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE userid = %s', (userid,))
        account = cursor.fetchone()
        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', userid):
            msg = 'User ID must contain only characters and numbers!'
        elif not username or not password or not email or not userid:
            msg = 'Please fill out the form!'
        else:
            cursor.execute('INSERT INTO users (username, password, email, userid, phone_number) VALUES (%s, %s, %s, %s, %s)', (username, password, email, userid, phone_number,))
            mysql.connection.commit()
            msg = 'You have successfully registered!'
    elif request.method == 'POST':
        msg = 'Please fill out the form!'
    return render_template('register.html', msg=msg)

@app.route('/calendar')
def calendar():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM events WHERE user_id = %s', (session['id'],))
        events = cursor.fetchall()
        return render_template('calendar.html', username=session['username'], events=events)
    return redirect(url_for('login'))

@app.route('/addevent', methods=['GET', 'POST'])
def addevent():
    if 'loggedin' in session:
        if request.method == 'POST' and 'title' in request.form and 'start_datetime' in request.form and 'end_datetime' in request.form:
            title = request.form['title']
            description = request.form['description']
            start_datetime = request.form['start_datetime']
            end_datetime = request.form['end_datetime']
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('INSERT INTO events (title, description, start_datetime, end_datetime, user_id) VALUES (%s, %s, %s, %s, %s)', (title, description, start_datetime, end_datetime, session['id'],))
            mysql.connection.commit()
            return redirect(url_for('calendar'))
        return render_template('addevent.html')
    return redirect(url_for('login'))

@app.route('/creategroup', methods=['GET', 'POST'])
def creategroup():
    if 'loggedin' in session:
        if request.method == 'POST' and 'group_name' in request.form:
            group_name = request.form['group_name']
            description = request.form['description']
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('INSERT INTO groupss (name, description) VALUES (%s, %s)', (group_name, description,))
            mysql.connection.commit()
            group_id = cursor.lastrowid
            cursor.execute('INSERT INTO user_groupss (user_id, group_id) VALUES (%s, %s)', (session['id'], group_id))
            mysql.connection.commit()
            return redirect(url_for('groupss'))
        return render_template('creategroup.html')
    return redirect(url_for('login'))

@app.route('/groupss')
def groupss():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT groupss.id, groupss.name FROM groupss JOIN user_groupss ON groupss.id = user_groupss.group_id WHERE user_groupss.user_id = %s', (session['id'],))
        groupss = cursor.fetchall()
        return render_template('groupss.html', username=session['username'], groupss=groupss)
    return redirect(url_for('login'))

@app.route('/invite', methods=['GET', 'POST'])
def invite():
    if 'loggedin' in session:
        if request.method == 'POST' and 'group_id' in request.form and 'userid' in request.form:
            group_id = request.form['group_id']
            userid = request.form['userid']
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT id FROM users WHERE userid = %s', (userid,))
            user = cursor.fetchone()
            if user:
                user_id = user['id']
                cursor.execute('INSERT INTO user_groupss (user_id, group_id) VALUES (%s, %s)', (user_id, group_id,))
                mysql.connection.commit()
                msg = 'User invited successfully!'
            else:
                msg = 'User not found!'
        return render_template('invite.html', msg=msg)
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
