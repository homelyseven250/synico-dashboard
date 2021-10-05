#   Copyright (c) 2021 George Keylock
#   All rights reserved.
from flask import Flask, jsonify, render_template, redirect, url_for, request, send_from_directory
from authlib.integrations.flask_client import OAuth
# import gunicorn
import requests, flask_login, flask_socketio, os, sched, time, json

s = sched.scheduler(time.time, time.sleep)
app = Flask(__name__)

# Import the config file
app.config.from_pyfile('config.py')
# Setup authlib for Discord
oauthCache = {}
oauth = OAuth(app)
login_manager = flask_login.LoginManager()
login_manager.init_app(app)
socket = flask_socketio.SocketIO(app)
botSID = None


@login_manager.user_loader
def load_user(user_id):
    user = User()
    user.id = user_id
    return user


discord = oauth.register(
    name='discord',
    client_id='887734783139012629',
    client_secret='L3tLMeTXpyItz3OMYUX4gv3wLOe5KRvB',
    access_token_url='https://discord.com/api/oauth2/token',
    access_token_params=None,
    authorize_url='https://discord.com/api/oauth2/authorize',
    authorize_params=None,
    api_base_url=app.config['DISCORD_API_BASE_URL'],
    client_kwargs={'scope': 'identify email guilds'},
    prompt='none'
)


class User(flask_login.UserMixin):
    pass


def getInviteURL(guild_id):
    return f'https://discord.com/oauth2/authorize?client_id=887734783139012629&scope=bot%20applications.commands&permissions=7784103761&guild_id={guild_id}&disable_guild_select=true&response_type=code&redirect_uri={url_for("invite_callback", _external=True)}'


def checkGuild(id):
    inGuilds = getBotGuilds()
    for guild in inGuilds:
        if guild['id'] == id:
            return True
    return False


def getBotGuilds():
    client = requests.session()
    client.headers.update(
        {'Authorization': 'Bot ' + app.config['DISCORD_BOT_TOKEN']})
    guilds = json.loads(client.get(
        app.config['DISCORD_API_BASE_URL'] + 'users/@me/guilds').text)
    return guilds


def getChannels(guild_id):
    client = requests.session()
    client.headers.update(
        {'Authorization': 'Bot ' + app.config['DISCORD_BOT_TOKEN']})
    channels = json.loads(client.get(
        app.config['DISCORD_API_BASE_URL'] + f'guilds/{guild_id}/channels').text)
    return channels


def getChannel(channel_id):
    client = requests.session()
    client.headers.update(
        {'Authorization': 'Bot ' + app.config['DISCORD_BOT_TOKEN']})
    channel = json.loads(client.get(
        app.config['DISCORD_API_BASE_URL'] + f'channels/{channel_id}').text)
    return channel


@app.route('/login/discord')
def login():
    return discord.authorize_redirect()


@app.route('/auth/discord')
def auth():
    token = discord.authorize_access_token()
    authdata = json.loads(discord.get('users/@me').text)
    id = authdata['id']
    username = authdata['username']+'#'+authdata['discriminator']
    email = authdata['email']
    # Create a user object
    user = User()
    user.id = id
    user.username = username
    user.email = email
    storagePath = os.path.join('data', str(id))
    print(storagePath)
    if os.path.exists(storagePath):
        userStorage = json.loads(
            open(os.path.join('data', id, 'user.json')).read())
        userStorage['username'] = username
        userStorage['email'] = email
        userStorage['id'] = id
        userStorage['discord'] = True
        userStorage['discord_token'] = token
        with open(os.path.join('data', id, 'user.json'), 'w') as outfile:
            json.dump(userStorage, outfile)
    else:
        os.makedirs(os.path.join('data', id))
        userStorage = {}
        userStorage['username'] = username
        userStorage['email'] = email
        userStorage['id'] = id
        userStorage['discord'] = True
        userStorage['discord_token'] = token
        userStorage['guilds'] = []
        with open(os.path.join('data', id, 'user.json'), 'w') as outfile:
            json.dump(userStorage, outfile)

    flask_login.login_user(user)
    return redirect(url_for('dashboard'))


@app.route('/')
def index():
    if flask_login.current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/dashboard')
@flask_login.login_required
def dashboard():
    user = json.loads(open(os.path.join(
        'data', flask_login.current_user.get_id(), 'user.json')).read())
    if os.path.exists(os.path.join('data', flask_login.current_user.get_id(), 'guilds.json')):
        ownedGuilds = json.loads(open(os.path.join(
            'data', flask_login.current_user.get_id(), 'guilds.json')).read())
    else:
        client = requests.session()
        client.headers.update(
            {'Authorization': 'Bearer ' + user["discord_token"]["access_token"]})
        guilds = json.loads(client.get(
            app.config['DISCORD_API_BASE_URL'] + 'users/@me/guilds').text)
        ownedGuilds = []
        for guild in guilds:
            if guild['owner'] == True:
                ownedGuilds.append(guild)
        json.dump(ownedGuilds, open('data/'+user["id"]+'/guilds.json', 'w'))
    return render_template('dashboard.html', username=user["username"], guilds=ownedGuilds, user=user, botGuilds=getBotGuilds())


@app.route('/logout')
def logout():
    flask_login.logout_user()
    return redirect(url_for('index'))


@app.route('/dashboard/guild/<guild_id>')
@flask_login.login_required
def guild(guild_id):
    if checkGuild(guild_id):
        user = json.loads(open(os.path.join(
            'data', flask_login.current_user.get_id(), 'user.json')).read())
        if not os.path.exists(os.path.join('data', guild_id, 'guild.json')):
            os.makedirs(os.path.join('data', guild_id))
            guild = open(os.path.join('data', guild_id, 'guild.json'), 'w')
            guild.write(json.dumps({'guild_id': guild_id}))
            guild.close()
        guild = json.loads(
            open(os.path.join('data', guild_id, 'guild.json')).read())
        if not guild_id in user['guilds']:
            user['guilds'].append(guild_id)
            with open(os.path.join('data', flask_login.current_user.get_id(), 'user.json'), 'w') as outfile:
                json.dump(user, outfile)
        return render_template('guild.html', guild=guild, user=user, username=user["username"], guild_id=guild_id)
    else:
        return redirect(getInviteURL(guild_id))


@app.route('/dashboard/guild/<guild_id>/channels/<channel_id>/msg')
@flask_login.login_required
def guild_msg(guild_id, channel_id):
    msg = request.args.get('message')
    user = json.loads(open(os.path.join(
        'data', flask_login.current_user.get_id(), 'user.json')).read())
    if guild_id in user['guilds']:
        socket.emit(
            'msg', {'message': msg, 'channel_id': channel_id, 'guild_id': guild_id})
    return jsonify({'status': 'success', 'handover': True})


@app.route('/dashboard/guild/<guild_id>/channels')
@flask_login.login_required
def guild_channels(guild_id):
    user = json.loads(open(os.path.join(
        'data', flask_login.current_user.get_id(), 'user.json')).read())
    if guild_id in user['guilds']:
        channels = getChannels(guild_id)
        textChannels = []
        for channel in channels:
            if channel['type'] == 0 or channel['type'] == 5:
                textChannels.append(channel)
        return render_template('channels.html', channels=textChannels, guild_id=guild_id)

    else:
        return redirect(getInviteURL(guild_id))


@app.route('/dashboard/guild/<guild_id>/channels/<channel_id>')
@flask_login.login_required
def guild_channel(guild_id, channel_id):
    user = json.loads(open(os.path.join(
        'data', flask_login.current_user.get_id(), 'user.json')).read())
    if guild_id in user['guilds']:
        channel = getChannel(channel_id)
        return render_template('channel.html', channel=channel, guild_id=guild_id)
    else:
        return redirect(getInviteURL(guild_id))


@app.route('/dashboard/admin')
@flask_login.login_required
def admin():
    user = json.loads(open(os.path.join(
        'data', flask_login.current_user.get_id(), 'user.json')).read())
    if user['admin'] == True:
        return render_template('admin.html', user=user, username=user['username'], allGuildsLength=len(getBotGuilds()))
    else:
        return redirect(url_for('dashboard'))

@app.route('/invite/callback')
def invite_callback():
    return redirect(f'/dashboard/guild/{request.args.get("guild_id")}')

@socket.on('ping')
def pingSocket():
    socket.emit('pong')
    socket.emit('reportEvent', {'innerHTML': render_template('report.html', user='AcidFilms', message='Test'), 'user': 'AcidFilms'})



@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'logo.png', mimetype='image/png')

@socket.on('connect')
def connection(data):
    global botSID
    if data:
        if data['key'] == app.config['BOT_KEY']:
            botSID = request.sid
        else:
            print("Bot presented incorrect auth key - rejecting")
            print(data['key'])

@socket.on('pingBot')
def pingBot():
    if botSID:
        socket.emit('ping', to=botSID)
        socket.emit('pinged', to=request.sid)

@socket.on('pong')
def pong():
    socket.emit('botStatus', {"status": "OK"}, broadcast=True)

@socket.on('settingsChange')
def settingsChange(data):
    socket.emit('settingsChange', data, to=botSID)

# @socket.on('getWarnings')
# def getWarnings(data):
#     socket.emit('getWarnings', {"guildID": data['guildID']}, to=botSID)

if __name__ == '__main__':
    socket.run(app)
