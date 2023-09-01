from models.play_model import make_answer ,get_room_dict, get_user
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user, login_required
from models.play_model import room_data_manager
play_bp = Blueprint('play', __name__, url_prefix='')

@play_bp.route('/single-play', methods=['GET', 'POST'])
def single_play():
    return render_template('single_game.html',current_user=current_user)

@play_bp.get("/get-room-dict")
@login_required
def get_room_dictAll():
    return get_room_dict()

@play_bp.get("/get_user_info")
@login_required
def get_user_info():
    return get_user()

@play_bp.get('/multi_game')
@login_required
def chat():
    room_name = request.args.get('room_name')
    user_name = current_user.name
    if room_data_manager.is_user_in_room(user_name, room_name):
         flash("이미 방에 입장해 있습니다.", "warning")
         return redirect(url_for('index'))
    return render_template('multi_game/multi_game.html',current_user=current_user)

@play_bp.post('/multi_game')
@login_required
def chat_post():
    mission_id = request.args.get('id')
    make_answer(mission_id, request.args.get('room_name'))
    return render_template('multi_game/multi_game.html',current_user=current_user)
