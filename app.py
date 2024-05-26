from flask import Flask
from flask import request
app = Flask(__name__)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['Username']
        password = request.form['PW']
        return f'Logged in as {username}'
    return '''
        <form method="post">
            Username: <input type="text" name="Username"><br>
            Password: <input type="password" name="password"><br>
            <input type="submit" value="Login">
        </form>
    '''

@app.route('/')
def hello_world():
    return 'Hello world'

@app.route('/user')
def show_user():
    return 'User name is'

if __name__ == '__main__':
    app.run(debug=True)