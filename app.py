import os
import re
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'uploads'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1234'
app.config['MYSQL_DB'] = 'calendar_db'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'ppt', 'pptx', 'hwp', 'py', 'c'}

mysql = MySQL(app)

def secure_hangul_filename(filename):
    filename = re.sub(r'[^a-zA-Z0-9가-힣_.-]', '_', filename)
    return filename

@app.route('/')
def home():
    return render_template('home_ver2.html')

@app.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '데이터 형식이 잘못되었습니다.'}), 400

        email = data.get('email')
        name = data.get('name')
        username = data.get('username')
        password = data.get('password')
        hashed_password = generate_password_hash(password)

        cursor = mysql.connection.cursor()

        # Check if email or username already exists
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        email_exists = cursor.fetchone()
        
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        username_exists = cursor.fetchone()

        if email_exists:
            return jsonify({'success': False, 'message': '이미 존재하는 이메일입니다.'})
        
        if username_exists:
            return jsonify({'success': False, 'message': '이미 존재하는 사용자 이름입니다.'})

        sql = "INSERT INTO users (email, name, username, password) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (email, name, username, hashed_password))
        mysql.connection.commit()
        return jsonify({'success': True, 'redirect': url_for('home')})
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': '서버 내부 오류가 발생했습니다.'}), 500
    finally:
        cursor.close()

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '데이터 형식이 잘못되었습니다.'}), 400

        username = data.get('username')
        password = data.get('password')

        cursor = mysql.connection.cursor()
        sql = "SELECT * FROM users WHERE username = %s"
        cursor.execute(sql, (username,))
        user = cursor.fetchone()
        cursor.close()

        if user:
            stored_hash = user[3]
            is_password_correct = check_password_hash(stored_hash, password)
        else:
            return jsonify({'success': False, 'message': '사용자를 찾을 수 없습니다.'}), 404

        if user and is_password_correct:
            session['username'] = user[2]
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': '비밀번호가 일치하지 않습니다.'}), 401
    except Exception as e:
        return jsonify({'success': False, 'message': '서버 내부 오류가 발생했습니다.'}), 500

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/personal_calendar')
def personal_calendar():
    if 'username' in session:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT name FROM users WHERE username = %s", (session['username'],))
        user_name = cursor.fetchone()[0]
        cursor.close()
        return render_template('personal_calendar.html', username=session['username'], user_name=user_name)
    else:
        return redirect(url_for('home'))

@app.route('/group_calendar/<int:group_id>')
def group_calendar(group_id):
    if 'username' in session:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT name FROM groupss WHERE id = %s", (group_id,))
        group_name = cursor.fetchone()[0]
        cursor.close()
        return render_template('group_calendar.html', group_id=group_id, group_name=group_name)
    else:
        return redirect(url_for('home'))


@app.route('/grouppage')
def group_page():
    if 'username' in session:
        return render_template('grouppage.html', username=session['username'])
    else:
        return redirect(url_for('home'))

@app.route('/add_group', methods=['POST'])
def add_group():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '데이터 형식이 잘못되었습니다.'}), 400

        group_name = data.get('name')

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id FROM users WHERE username = %s", (session['username'],))
        user_id = cursor.fetchone()[0]

        cursor.execute("INSERT INTO groupss (name, owner_id) VALUES (%s, %s)", (group_name, user_id))
        group_id = cursor.lastrowid

        cursor.execute("INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)", (group_id, user_id))
        mysql.connection.commit()
        return jsonify({'success': True})
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': '서버 내부 오류가 발생했습니다.'}), 500
    finally:
        cursor.close()

@app.route('/delete_group/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    if 'username' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id FROM users WHERE username = %s", (session['username'],))
        user_id = cursor.fetchone()[0]

        # 그룹 소유자인지 확인
        cursor.execute("SELECT owner_id FROM groupss WHERE id = %s", (group_id,))
        owner_id = cursor.fetchone()[0]

        if user_id != owner_id:
            return jsonify({'success': False, 'message': '그룹 삭제 권한이 없습니다.'}), 403

        # 그룹 삭제
        cursor.execute("DELETE FROM group_members WHERE group_id = %s", (group_id,))
        cursor.execute("DELETE FROM group_events WHERE group_id = %s", (group_id,))
        cursor.execute("DELETE FROM groupss WHERE id = %s", (group_id,))
        mysql.connection.commit()
        return jsonify({'success': True})
    except Exception as e:
        mysql.connection.rollback()
        print("Exception in delete_group:", str(e))
        return jsonify({'success': False, 'message': '서버 내부 오류가 발생했습니다.', 'error': str(e)}), 500
    finally:
        cursor.close()

@app.route('/leave_group/<int:group_id>', methods=['POST'])
def leave_group(group_id):
    if 'username' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id FROM users WHERE username = %s", (session['username'],))
        user_id = cursor.fetchone()[0]

        # 그룹 소유자인지 확인
        cursor.execute("SELECT owner_id FROM groupss WHERE id = %s", (group_id,))
        owner_id = cursor.fetchone()[0]

        cursor.execute("DELETE FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, user_id))

        # 그룹의 남은 멤버 수 확인
        cursor.execute("SELECT user_id FROM group_members WHERE group_id = %s", (group_id,))
        remaining_members = cursor.fetchall()

        if len(remaining_members) == 0:
            # 마지막 멤버가 탈퇴하는 경우 그룹 삭제
            cursor.execute("DELETE FROM group_events WHERE group_id = %s", (group_id,))
            cursor.execute("DELETE FROM groupss WHERE id = %s", (group_id,))
        elif user_id == owner_id:
            # 그룹 소유자가 탈퇴하는 경우 남은 멤버 중 한 명에게 소유권 이전
            new_owner_id = remaining_members[0][0]
            cursor.execute("UPDATE groupss SET owner_id = %s WHERE id = %s", (new_owner_id, group_id))

        mysql.connection.commit()
        return jsonify({'success': True})
    except Exception as e:
        mysql.connection.rollback()
        print("Exception in leave_group:", str(e))
        return jsonify({'success': False, 'message': '서버 내부 오류가 발생했습니다.', 'error': str(e)}), 500
    finally:
        cursor.close()

@app.route('/get_groups', methods=['GET'])
def get_groups():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id FROM users WHERE username = %s", (session['username'],))
        user_id = cursor.fetchone()[0]

        cursor.execute("SELECT g.id, g.name, g.owner_id FROM groupss g JOIN group_members gm ON g.id = gm.group_id WHERE gm.user_id = %s", (user_id,))
        groups = cursor.fetchall()
        return jsonify({'success': True, 'groups': [{'id': group[0], 'name': group[1], 'is_owner': user_id == group[2]} for group in groups]})
    except Exception as e:
        print("Exception in get_groups:", str(e))
        return jsonify({'success': False, 'message': '서버 내부 오류가 발생했습니다.', 'error': str(e)}), 500
    finally:
        cursor.close()


@app.route('/get_group_members/<int:group_id>', methods=['GET'])
def get_group_members(group_id):
    if 'username' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT u.username FROM users u JOIN group_members gm ON u.id = gm.user_id WHERE gm.group_id = %s", (group_id,))
        members = cursor.fetchall()
        cursor.close()
        return jsonify({'success': True, 'members': [{'username': member[0]} for member in members]})
    except Exception as e:
        print("Exception in get_group_members:", str(e))
        return jsonify({'success': False, 'message': '서버 내부 오류가 발생했습니다.', 'error': str(e)}), 500

@app.route('/add_event', methods=['POST'])
def add_event():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '데이터 형식이 잘못되었습니다.'}), 400

        event_title = data.get('title')
        event_date = data.get('date')

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id FROM users WHERE username = %s", (session['username'],))
        user_id = cursor.fetchone()[0]

        cursor.execute("INSERT INTO events (title, date, user_id) VALUES (%s, %s, %s)", (event_title, event_date, user_id))
        mysql.connection.commit()
        return jsonify({'success': True})
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': '서버 내부 오류가 발생했습니다.'}), 500
    finally:
        cursor.close()

@app.route('/get_events', methods=['GET'])
def get_events():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id FROM users WHERE username = %s", (session['username'],))
        user_id = cursor.fetchone()[0]

        cursor.execute("SELECT title, date FROM events WHERE user_id = %s", (user_id,))
        events = cursor.fetchall()
        cursor.close()
        return jsonify({'success': True, 'events': [{'title': event[0], 'date': event[1].strftime('%Y-%m-%d')} for event in events]})
    except Exception as e:
        print("Exception in get_events:", str(e))  # 로그에 예외 메시지를 출력합니다.
        return jsonify({'success': False, 'message': '서버 내부 오류가 발생했습니다.', 'error': str(e)}), 500

@app.route('/get_group_events/<int:group_id>', methods=['GET'])
def get_group_events(group_id):
    if 'username' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT title, date FROM group_events WHERE group_id = %s", (group_id,))
        events = cursor.fetchall()
        cursor.close()
        return jsonify({'success': True, 'events': [{'title': event[0], 'date': event[1].strftime('%Y-%m-%d')} for event in events]})
    except Exception as e:
        return jsonify({'success': False, 'message': '서버 내부 오류가 발생했습니다.'}), 500

@app.route('/add_group_event', methods=['POST'])
def add_group_event():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '데이터 형식이 잘못되었습니다.'}), 400

        event_title = data.get('title')
        event_date = data.get('date')
        group_id = data.get('group_id')

        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO group_events (title, date, group_id) VALUES (%s, %s, %s)", (event_title, event_date, group_id))
        mysql.connection.commit()
        cursor.close()
        return jsonify({'success': True})
    except Exception as e:
        print("Exception in add_group_event:", str(e))
        return jsonify({'success': False, 'message': '서버 내부 오류가 발생했습니다.', 'error': str(e)}), 500


@app.route('/delete_event', methods=['POST'])
def delete_event():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    try:
        data = request.get_json()
        if not data or 'date' not in data:
            return jsonify({'success': False, 'message': '데이터 형식이 잘못되었습니다.'}), 400

        event_date = data['date']

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id FROM users WHERE username = %s", (session['username'],))
        user_id = cursor.fetchone()[0]

        cursor.execute("DELETE FROM events WHERE user_id = %s AND date = %s", (user_id, event_date))
        mysql.connection.commit()
        return jsonify({'success': True})
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': '서버 내부 오류가 발생했습니다.'}), 500
    finally:
        cursor.close()

@app.route('/delete_group_event', methods=['POST'])
def delete_group_event():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    try:
        data = request.get_json()
        if not data or 'date' not in data or 'group_id' not in data:
            return jsonify({'success': False, 'message': '데이터 형식이 잘못되었습니다.'}), 400

        event_date = data['date']
        group_id = data['group_id']

        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM group_events WHERE group_id = %s AND date = %s", (group_id, event_date))
        mysql.connection.commit()
        return jsonify({'success': True})
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': '서버 내부 오류가 발생했습니다.'}), 500
    finally:
        cursor.close()

@app.route('/invite_member', methods=['POST'])
def invite_member():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '데이터 형식이 잘못되었습니다.'}), 400

        group_id = data.get('group_id')
        recipient_username = data.get('username')

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id FROM users WHERE username = %s", (session['username'],))
        sender_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM users WHERE username = %s", (recipient_username,))
        recipient = cursor.fetchone()
        if not recipient:
            return jsonify({'success': False, 'message': '해당 사용자가 존재하지 않습니다.'})

        recipient_id = recipient[0]

        cursor.execute("INSERT INTO group_invitations (group_id, sender_id, recipient_id) VALUES (%s, %s, %s)",
                       (group_id, sender_id, recipient_id))
        mysql.connection.commit()
        return jsonify({'success': True})
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': '서버 내부 오류가 발생했습니다.'}), 500
    finally:
        cursor.close()

@app.route('/get_invitations', methods=['GET'])
def get_invitations():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id FROM users WHERE username = %s", (session['username'],))
        user_id = cursor.fetchone()[0]

        cursor.execute("SELECT gi.id, g.name, u.username, gi.status FROM group_invitations gi JOIN groupss g ON gi.group_id = g.id JOIN users u ON gi.sender_id = u.id WHERE gi.recipient_id = %s", (user_id,))
        invitations = cursor.fetchall()
        cursor.close()
        return jsonify({'success': True, 'invitations': [{'id': inv[0], 'group_name': inv[1], 'sender': inv[2], 'status': inv[3]} for inv in invitations]})
    except Exception as e:
        print("Exception in get_invitations:", str(e))
        return jsonify({'success': False, 'message': '서버 내부 오류가 발생했습니다.', 'error': str(e)}), 500

@app.route('/respond_invitation', methods=['POST'])
def respond_invitation():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    try:
        data = request.get_json()
        invitation_id = data.get('invitation_id')
        response = data.get('response')

        if response not in ['accepted', 'rejected']:
            return jsonify({'success': False, 'message': '잘못된 응답입니다.'}), 400

        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE group_invitations SET status = %s WHERE id = %s", (response, invitation_id))

        if response == 'accepted':
            cursor.execute("SELECT group_id, recipient_id FROM group_invitations WHERE id = %s", (invitation_id,))
            invitation = cursor.fetchone()
            group_id, user_id = invitation[0], invitation[1]
            cursor.execute("INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)", (group_id, user_id))

        mysql.connection.commit()
        return jsonify({'success': True})
    except Exception as e:
        mysql.connection.rollback()
        print("Exception in respond_invitation:", str(e))
        return jsonify({'success': False, 'message': '서버 내부 오류가 발생했습니다.', 'error': str(e)}), 500
    finally:
        cursor.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload_group_file', methods=['POST'])
def upload_group_file():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    if 'file' not in request.files or not request.files['file'].filename:
        return jsonify({'success': False, 'message': '파일이 필요합니다.'}), 400

    file = request.files['file']
    group_id = request.form['group_id']

    if file and allowed_file(file.filename):
        filename = secure_hangul_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Ensure the upload directory exists
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        
        file.save(file_path)

        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO group_files (group_id, file_name, file_path) VALUES (%s, %s, %s)", (group_id, filename, file_path))
        mysql.connection.commit()
        cursor.close()

        return jsonify({'success': True, 'message': '파일이 업로드되었습니다.'})
    else:
        return jsonify({'success': False, 'message': '허용되지 않는 파일 형식입니다.'}), 400

@app.route('/download_group_file/<int:file_id>', methods=['GET'])
def download_group_file(file_id):
    if 'username' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT file_name, file_path FROM group_files WHERE id = %s", (file_id,))
    file_data = cursor.fetchone()
    cursor.close()

    if file_data:
        file_name, file_path = file_data
        return send_from_directory(directory=os.path.dirname(file_path), path=os.path.basename(file_path), as_attachment=True)
    else:
        return jsonify({'success': False, 'message': '파일을 찾을 수 없습니다.'}), 404

@app.route('/delete_group_file/<int:file_id>', methods=['DELETE'])
def delete_group_file(file_id):
    if 'username' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT file_path FROM group_files WHERE id = %s", (file_id,))
        file_data = cursor.fetchone()
        if file_data:
            file_path = file_data[0]
            if os.path.exists(file_path):
                os.remove(file_path)
            cursor.execute("DELETE FROM group_files WHERE id = %s", (file_id,))
            mysql.connection.commit()
            return jsonify({'success': True, 'message': '파일이 삭제되었습니다.'})
        else:
            return jsonify({'success': False, 'message': '파일을 찾을 수 없습니다.'}), 404
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': '서버 내부 오류가 발생했습니다.'}), 500
    finally:
        cursor.close()

@app.route('/get_group_files/<int:group_id>', methods=['GET'])
def get_group_files(group_id):
    if 'username' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, file_name FROM group_files WHERE group_id = %s", (group_id,))
    files = cursor.fetchall()
    cursor.close()

    return jsonify({'success': True, 'files': [{'id': file[0], 'name': file[1]} for file in files]})

if __name__ == '__main__':
    app.run(debug=True)

