from flask import Flask, jsonify, render_template, redirect, url_for
from authlib.integrations.flask_client import OAuth
import json
# import gunicorn
import requests
import flask_login
import flask_socketio
import os

app = Flask(__name__)

# Import the config file
app.config.from_pyfile('config.py')
# Setup authlib for Discord
oauthCache = {}
oauth = OAuth(app)
login_manager = flask_login.LoginManager()
login_manager.init_app(app)
socket = flask_socketio.SocketIO(app)


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
        userStorage ['guilds'] = []
        with open(os.path.join('data', id, 'user.json'), 'w') as outfile:
            json.dump(userStorage, outfile)
    
    flask_login.login_user(user)
    return redirect(url_for('dashboard'))


@app.route('/')
def index():
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
    return render_template('dashboard.html', username=user["username"], guilds=ownedGuilds, user=user)


@app.route('/logout')
def logout():
    flask_login.logout_user()
    return redirect(url_for('index'))


@app.route('/dashboard/guild/<guild_id>')
@flask_login.login_required
def guild(guild_id):
    user = json.loads(open(os.path.join(
        'data', flask_login.current_user.get_id(), 'user.json')).read())
    if not os.path.exists(os.path.join('data', guild_id, 'guild.json')):
        os.makedirs(os.path.join('data', guild_id))
        guild = open(os.path.join('data', guild_id, 'guild.json'), 'w')
        guild.write(json.dumps({'guild_id': guild_id}))
        guild.close()
    guild = json.loads(open(os.path.join('data', guild_id, 'guild.json')).read())
    return render_template('guild.html', guild=guild, user=user, username=user["username"])


@app.route('/refreshGuilds')
@flask_login.login_required
def refreshGuilds():
    socket.emit('guildCheck', {'uid': flask_login.current_user.get_id()})
    return "OK"

@ socket.on('guildCheckReply')
def guildCheckReply(data):
    for guild in data['cache']:
        userFile = open(os.path.join('data', data['uid'], 'user.json'), 'r')
        user = json.loads(userFile.read())
        userFile.close()
        if guild['id'] in user['guilds']:
            pass
        elif guild['ownerId'] == data['uid']:
            user['guilds'].append(guild['id'])
            userFile = open(os.path.join('data', data['uid'], 'user.json'), 'w')
            userFile.write(json.dumps(user))
            userFile.close()


socket.run(app)
