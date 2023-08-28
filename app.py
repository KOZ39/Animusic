#flask main --author: NewKyaru 11/08/2023
import os
from decouple import config
from flask import Flask,render_template, request, redirect, url_for, jsonify, flash, send_file
from flask_login import LoginManager, current_user, login_required, logout_user
from chat.chat import socketio, get_room_dict, get_user
from chat.chat_model import make_answer
from controllers import play_controller, login_controller
from models import login_model
import requests
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
app = Flask(__name__)
app.config['SECRET_KEY'] = config('SECRET_KEY')

login_manager = LoginManager()
login_manager.init_app(app)

socketio.init_app(app)

@app.get('/get-music-data')
def get_music_data():
    mission_id = request.args.get('id')
    return play_controller.single_make_answer(mission_id)

@login_manager.user_loader
def load_user(user_id):
    return login_model.get_user_by_id(user_id)

@app.route('/single_list')
def single_select():
    missions = play_controller.show_mission()
    return render_template('single_select.html', current_user=current_user,missions=missions)

@app.route('/single-play', methods=['GET', 'POST'])
def single_play():
    return render_template('single_game.html',current_user=current_user)

@app.route('/')
def index():
    return render_template('index.html', current_user=current_user)

@app.route('/play', methods=['GET', 'POST'])
def play():
    return play_controller.play_controller()

@app.route('/Show')
def show():
    return play_controller.show_table()

@app.route('/submit-to-db', methods=['POST'])
def submit():
    return play_controller.submit_to_db()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    if request.method == 'POST':
        login_successful = login_controller.user_controller()
        if login_successful:
            return redirect(url_for('index'))

        flash('Invalid email or password')
        return redirect(url_for('login'))


#인증 관련 부분
@app.get('/login/google')
def google_login():
    return login_controller.google_login()


@app.get('/login/google/callback')
def google_callback():
    return login_controller.google_callback()


@app.get('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        return login_controller.register()
    return render_template('register.html')

#----------회원 탈퇴 & 회원 정보수정-----------
@app.get('/delete_account_confirm')
def delete_account_confirm():
    return render_template('account_management/deleteAccountConfirm.html')

@app.get('/delete_account')
def deleting_account():
    print(f"\033[92;1m{current_user.name}님의 회원탈퇴 시도중...\033[0m")
    result_delete_account = login_model.delete_account()
    if result_delete_account:
        print("\033[92;1m회원 탈퇴처리 완료\033[0m")
        return render_template('account_management/deleteAccountComplete.html')
    else:
        print("\033[92;1m회원 탈퇴처리 실패\033[0m")
        return render_template('account_management/deleteAccountFail.html')
@app.get('/account_confirm')
def account_confirm():
    print("체크 중: ", current_user.is_authenticated)
    if current_user.is_authenticated == False:
        return render_template('account_management/accountConfirm.html')
    else:
        return render_template('account_management/managementAccountPage.html')
@app.route('/get_current_user_is_google_authenticated', methods=['GET'])
def get_current_user_is_google_authenticated():
    return jsonify({'check_googleuser': current_user.is_google_authenticated})

@app.route('/update_profile', methods=['POST'])
def update_profile():
    data = request.json
    nickname = data[0]['nickname']
    password = data[0]['password']
    newpassword = data[0]['newpassword']

    if current_user.is_google_authenticated: # 구글 유저 인 경우
        if login_model.account_insert_in_googleuser(nickname):
            print(f"\033[92;1m사용자의 닉네임이 {nickname}으로 변경되었습니다.\033[0m")
            return jsonify({'message': '변경이 완료되었습니다.'}), 200
        else:
            print("\033[92;1m이미 존재하는 닉네임을 가진 회원이 있으므로 변경할 수 없습니다.\033[0m")
            return jsonify({'message': '이미 동일한 닉네임이 존재합니다.'}), 400
    else:
        if login_model.account_insert(nickname, password, newpassword):
            print("\033[92;1m사용자의 회원정보가 변경되었습니다.\033[0m")
            return jsonify({'message': '변경이 완료되었습니다.'}), 200
        else:
            print("\033[92;1m사용자의 회원정보 변경이 실패하였습니다.\033[0m")
            return jsonify({'message': '기존 비밀번호가 일치하지 않거나 동일한 닉네임이 존재합니다.'}), 400

# 캐릭터 변경기능
@app.route('/select_character')
def select_character():
    character_list = [file for file in os.listdir('static/img/character')]
    print("캐릭터 이미지파일 리스트: ", character_list)
    return render_template('account_management/selectCharacter.html', character_list=character_list)

@app.route('/insert_character', methods=['POST'])
def insert_character():
    character_number = request.get_json().get('character_number')
    return login_model.insert_character_number(character_number)
# -------------------------------------
####################################################################################

#미션 관리부분
@app.route('/Map')
def mymap():
    data_list = play_controller.show_mission_byProducer()
    return render_template('Map.html', data_list=data_list)

@app.post('/update-to-db')
def update():
    return play_controller.update_to_db()


@app.get("/delete-mission")
def deleteMission():
    return play_controller.delete_Mission(request.args.get('id'))

@app.route('/download_excelfile', methods=['GET'])
def download_template():
    return send_file('static/file_form/MakingMap_form.xlsx', as_attachment=True)

@app.route('/check_videoid', methods=['POST'])
#재생가능한 비디오링크인지 체크해주는 기능(요청 1번에 최대 42개의 비디오링크까지 가능)
def check_videoid():
    videoid_list, convert_list = set(request.get_json()), set()
    result = videoid_list.copy()
    for id_count, videoid in enumerate(videoid_list):
        convert_list.add("&id=" + videoid)
        if (id_count + 1) % 42 == 0:
            request_text = "".join(map(str, convert_list))
            api_result = requests.get(f'https://www.googleapis.com/youtube/v3/videos?key={config("YOUTUBE_API_KEY")}&part=status{request_text}')
            renewable_list = set(item['id'] for item in api_result.json()['items'] if item['status']['embeddable'])
            result -= renewable_list
            convert_list.clear()
    if len(convert_list) > 0:
        request_text = "".join(map(str, convert_list))
        api_result = requests.get(f'https://www.googleapis.com/youtube/v3/videos?key={config("YOUTUBE_API_KEY")}&part=status{request_text}')
        renewable_list = set(item['id'] for item in api_result.json()['items'] if item['status']['embeddable'])
        result -= renewable_list
    return jsonify(list(result))

#########################################################################################

@app.route('/room_list')
def room_list():
    if current_user.is_authenticated == False:
        user_id = ""
        print(f"로그인 되어있지 않으므로 멀티플레이는 불가합니다.")
    else:
        user_id = current_user.name
        print(f"{user_id} 유저 아이디 확인됨.")
    return render_template('room_list.html')


@app.get("/get-room-dict")
def get_room_dictAll():
    return get_room_dict()

@app.get("/get_user_info")
def get_user_info():
    return get_user()

@app.get('/multi_game')
def chat():
    return render_template('multi_game/multi_game.html',current_user=current_user)

@app.post('/multi_game')
def chat_post():
    mission_id = request.args.get('id')
    make_answer(mission_id, request.args.get('room_name'))
    return render_template('multi_game/multi_game.html',current_user=current_user)

@app.get('/api/get_mission_table')
def get_mission_table():
    mission_table_data = play_controller.show_mission_active()
    return jsonify(mission_table_data)

if __name__ == '__main__':
    play_controller.ensure_tables_exist()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)

