from flask_socketio import emit,join_room
from flask import request
from flask_login import current_user
from models.play_model import room_data_manager
from Socket.socket import socket_class
from models.room_model import update_room_player_count
import time

tempRoomdict = {}
def room_Socket(socketio):
    @socketio.on('room_check')
    def room_check_sock(data):
        session_id = request.sid
        room_name = data['room_name'] 
        room_keys = room_data_manager._data_store.keys()
        room_key = str(max((int(key) for key in room_keys), default=0) + 1)
        if not room_data_manager.room_check(room_key):
            tempRoomdict[room_key] = {"room_name": room_name, "room_password" :data['room_password'], "room_max_human": data['room_max_human']}
            emit('Join_room', room_key, room=session_id)

    @socketio.on('create_room')
    def create_room_sock(data):
        session_id = request.sid
        room_key = data['room_key']
        if room_data_manager.create_room(room_key,session_id): 
            if room_key in tempRoomdict:
                room_data_manager._data_store[room_key]["room_info"]['room_name'] = tempRoomdict[room_key]["room_name"]
                room_data_manager._data_store[room_key]["room_info"]['room_password'] = tempRoomdict[room_key]["room_password"]
                room_data_manager._data_store[room_key]["room_info"]['room_full_user'] = tempRoomdict[room_key]["room_max_human"]
                tempRoomdict.pop(room_key)
            room_name = room_data_manager._data_store[room_key]["room_info"]['room_name']
            isPassword = False if room_data_manager._data_store[room_key]["room_info"]["room_password"] in ('', None) else True
            max_user = room_data_manager._data_store[room_key]["room_info"]["room_full_user"]
            emit('room_update', {'room_key': room_key,'room_name': room_name, "max_user": max_user, "is_password": isPassword}, broadcast=True)

    @socketio.on('join')
    def join_sock(data):
        room_key = data['room_key']
        session_id = request.sid
        room_data_manager.join(room_key,session_id,current_user, time)
        join_room(room_key)
        user_id = room_data_manager.host_setting(room_key)
        game_status = room_data_manager._data_store[room_key]['room_info']['room_status']
        if user_id != "":
            emit("host_updated", {"user":user_id, "game_status":game_status}, room=room_key)
        update_room_player_count(room_key, "님이 참가 하셨습니다.", room_data_manager._data_store[room_key]['user'][session_id]['username'])
        try:
            if current_user.name in socket_class.waitingroom_userlist:
                del socket_class.waitingroom_userlist[current_user.name]
                emit('update_waiting_userlist', socket_class.waitingroom_userlist, broadcast=True)
        except:
            pass
        
    @socketio.on("passwordCheckToServer")
    def password_check(data):
        room_key = data['room_key']
        if data['password'] == room_data_manager._data_store[room_key]["room_info"]["room_password"]:
            emit('Join_room', room_key, room=request.sid)
        else:
            emit('passwordFail',room=request.sid)
    @socketio.on('user_check')
    def user_check(data):
        user_name = current_user.name
        room_key = data['room_key']
        session_id = request.sid
        if room_data_manager.is_user_in_room(user_name,room_key):
            emit('user_check_not_ok', room=session_id)
        else :
            if room_data_manager.room_user_check(room_key) < int(room_data_manager._data_store[room_key]["room_info"]["room_full_user"]):
                if room_data_manager._data_store[room_key]["room_info"]["room_password"] is not None and room_data_manager._data_store[room_key]["room_info"]["room_password"] is not "":
                    emit("passwordCheck",room_key, room=session_id)
                else:
                    emit('Join_room',room_key, room=session_id)
            else : 
                emit("room_full_user", room_key, room=session_id)

    @socketio.on('playingStatus_true')
    def playingroom_hidden(room_key):
        room_data_manager.game_status(room_key,True)
        room_status = room_data_manager._data_store[room_key]["room_info"]["room_status"]
        room_data_manager.game_init(room_key)
        emit('request_room_changed', {"room_key":room_key,"room_status":room_status},  broadcast = True)

    @socketio.on('playingStatus_false')
    def playingroom_hidden(room_key):
        room_data_manager.game_status(room_key, False)
        room_status = room_data_manager._data_store[room_key]["room_info"]["room_status"]
        room_data_manager.game_init(room_key)
        emit('request_room_changed', {"room_key":room_key,"room_status":room_status},  broadcast = True)