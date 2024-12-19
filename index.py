from flask import Flask,render_template,request,session,redirect,url_for,jsonify
from flask_socketio import join_room , leave_room,send,SocketIO
import random
from string import ascii_uppercase
from cs50 import SQL


app = Flask(__name__)
app.config['SECRET_KEY'] = 'dafaf'
socketio=SocketIO(app)
db=SQL('sqlite:///mydb.db')



def generate_unique_code(length):
    while True :
        code=''
        for _ in range(length):
            code+=random.choice(ascii_uppercase)
        code_exist=None

        try:
            code_exist_indb=db.execute('select id from rooms where code = ?',code)
        except Exception:
            pass
        if code_exist_indb:
            generate_unique_code(length)
        else :
            return code



@app.route('/',methods=['POST','GET'])
def home():
    session.clear
    if request.method=='POST':
        name=request.form.get('name')
        code = request.form.get('code')
        join= request.form.get('join',False)
        create = request.form.get('create',False)

        if not name :
            return render_template('home.html',error='Please enter a name',code=code,name=name)
        if join != False and not code: #if they try to join !!
            return render_template('home.html',error='please enter a room code',code=code,name=name)
        

        room = code
        if create != False: #if CREATE
            room = generate_unique_code(4)
            print(f'room = {type(room)}')
            db.execute('insert into rooms (code,members) VALUES (?,?)',room,0)
            
    
        codeexist=db.execute('select * from rooms where code  = ? ',room)
        if not codeexist:
            return render_template('home.html',error='the room does not exist',code=code,name=name)
        
        session["room"]=room
        session["name"]=name
        return redirect(url_for("room"))
    return render_template('home.html')

import json

@app.route('/room')
def room():
    room=session.get('room')
    name=session.get('name')
    room_in_rooms=db.execute('select * from rooms where code = ? ', room)
    if room is None or name is None or not room_in_rooms:
        return redirect(url_for("home"))
    rows=db.execute('select name, message from messages where room_code = ? ',room)
    messages = [{"name": row["name"], "message": row["message"]} for row in rows]
    

    
    return render_template('room.html',code=room,messages=messages)

@socketio.on("message")
def message(data):
    room=session.get('room')
    room_in_rooms=db.execute('select id from rooms where code = ?',room)
    if not room_in_rooms:
        return
    name=session.get("name")
    message=data["data"]
    content={
        "name":name,
        "message":message
    }
    send(content,to=room)

    print(f'111 ={type(room)}')
    db.execute('INSERT INTO messages (room_code, name, message) VALUES (?, ?,?)',room,name, message)
    print(f'{session.get('name')} said : {data['data']}')



@socketio.on("connect")
def connect(auth):
    name=session.get('name')
    room=session.get('room')
    room_in_rooms=db.execute('select id from rooms where code = ?',room)
    if not room or not name:
        return 
    if not room_in_rooms:
        leave_room(room)
        return
    
    join_room(room)
    send({"name":name,"message":"has entered the room"},to=room)
    db.execute('UPDATE rooms SET members = members + 1 WHERE code = ?',room)
    print(f'{name} joined room: {room}')





@socketio.on("disconnect")
def disconnect():
    room=session.get("room")
    name=session.get("name")
    leave_room(room)
    roominrooms=db.execute('select id from rooms where code = ?',room)

    if roominrooms:
        db.execute('update rooms set members=members - 1 where code = ? ', room)
        member_count=db.execute('select members from rooms where code = ?', room)[0]['members']
        print(f'member count = {type(member_count)} ')
        print(f'member count = {member_count} ')
        if member_count== 0 :
            db.execute('delete from rooms where code = ?',room)
            db.execute('delete from messages where room_code = ?',room)
    send({"name":name,"message":"has left the room"},to=room)
    print(f'{name} has left ')

if __name__ == '__main__':
    socketio.run(app,debug=True)