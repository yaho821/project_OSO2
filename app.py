from flask import Flask, request, render_template, redirect, url_for
app = Flask(__name__)

@app.route('/')
def start():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['Username']
        password = request.form['PW']
        return redirect(url_for('person/<username>', username=username))
    return '''
        <form method="post">
            Username: <input type="text" name="Username"><br>
            Password: <input type="password" name="password"><br>
            <input type="submit" value="Login">
        </form>
        <p>
            <a href="/create_account">Create Account</a>
        </p>
        <p>
            <a href="/find_account">Find Account</a>
        </p>
    '''

@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':
        username = request.form['Username']
        password = request.form['PW']
        email = request.form['Email']
        return f'Account created for {username}'
    return '''
        <form method="post">
            Username: <input type="text" name="Username"><br>
            Password: <input type="password" name="password"><br>
            <input type="submit" value="Create Account">
        </form>
    '''

@app.route('/find_account', methods=['GET', 'POST'])
def find_account():
    if request.method == 'POST':
        email = request.form['Email']
    return '''
        <form method="post">
            Email: <input type="text" name="Email"><br>
            <input type="submit" value="Find Account">
        </form>
    ''' 

@app.route('/person/<username>')
def person_calender(username):
    return render_template("personcalender.html")

@app.route('/group/create', methods=['GET', 'POST'])
def create_group(groupname):
    return f'Group {groupname}'

@app.route('/group/<groupname>')
def group_calender(groupname):
    return render_template("groupcalender.html")
    
if __name__ == '__main__':
    app.run(debug=True)