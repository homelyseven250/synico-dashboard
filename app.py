#   Copyright (c) 2021 George Keylock
#   All rights reserved.
from json.decoder import JSONDecodeError
import time
import json
import os

import flask_login
import flask_socketio
# import gunicorn
import requests
import werkzeug.utils
import markdownify
from authlib.integrations.flask_client import OAuth
from flask import Flask, render_template, redirect, url_for, request, send_from_directory, abort, jsonify

app = Flask(__name__)

# Import the config file
app.config.from_pyfile('config.py')
# Setup authlib for Discord
oauthCache = {}
oauth = OAuth(app)
login_manager = flask_login.LoginManager()
login_manager.init_app(app)
socket = flask_socketio.SocketIO(app, ping_timeout=60)
botSID = None


@login_manager.user_loader
def load_user(user_id):
    # This is very simple - I copied and pasted it from some other code of mine.
    user = User()
    user.id = user_id
    return user


# Register OAuth for discord.
discord = oauth.register(
    name='discord',
    client_id=app.config['DISCORD_BOT_ID'],
    client_secret=app.config['OAUTH2_SECRET'],
    access_token_url=app.config['DISCORD_API_BASE_URL'] + 'oauth2/token',
    access_token_params=None,
    authorize_url='https://discord.com/oauth2/authorize',
    authorize_params=None,
    api_base_url=app.config['DISCORD_API_BASE_URL'],
    client_kwargs={'scope': 'identify email guilds'},
    prompt='none'
)


# Use the default flask_login user mixin.
class User(flask_login.UserMixin):
    pass


# Get an invite url for the guild id. This will probably be altered for production.
def getInviteURL(guild_id):
    return f'https://discord.com/oauth2/authorize?client_id={app.config["DISCORD_BOT_ID"]}&scope=bot%20applications.commands&permissions=8&guild_id={guild_id}&disable_guild_select=true&response_type=code&redirect_uri={url_for("invite_callback", _external=True)}'


# Check if a bot is in a specific guild via the discord API.
def checkGuild(id):
    inGuilds = getBotGuilds()
    for guild in inGuilds:
        if guild['id'] == id:
            return True
    return False


# Get a list of all guilds the bot is in.
def getBotGuilds():
    client = requests.session()
    client.headers.update(
        {'Authorization': 'Bot ' + app.config['DISCORD_BOT_TOKEN']})
    guilds = json.loads(client.get(
        app.config['DISCORD_API_BASE_URL'] + 'users/@me/guilds').text)
    return guilds


# Use the discord API to get a list of all channels in a guild.
def getChannels(guild_id):
    client = requests.session()
    client.headers.update(
        {'Authorization': 'Bot ' + app.config['DISCORD_BOT_TOKEN']})
    channels = json.loads(client.get(
        app.config['DISCORD_API_BASE_URL'] + f'guilds/{guild_id}/channels').text)
    return channels


# Get data for a specific channel id.
def getChannel(channel_id):
    client = requests.session()
    client.headers.update(
        {'Authorization': 'Bot ' + app.config['DISCORD_BOT_TOKEN']})
    channel = json.loads(client.get(
        app.config['DISCORD_API_BASE_URL'] + f'channels/{channel_id}').text)
    return channel


# Redirect to discord login
@app.route('/login/discord')
def login():
    return discord.authorize_redirect(url_for('auth', _external=True))


@app.route('/auth/discord')
def auth():
    token = discord.authorize_access_token()  # Get the token
    authdata = json.loads(discord.get('users/@me').text)  # Get user data
    # Get data
    id = authdata['id']
    # Combine username and the number after it,
    #  as this is what the end user will expect.
    username = authdata['username'] + '#' + authdata['discriminator']
    email = authdata['email']
    # Create a user object with email, id and the username
    user = User()
    user.id = id
    user.username = username
    user.email = email
    # Where we will store user's data
    storagePath = os.path.join('data', str(id))
    if os.path.exists(storagePath):  # Is the user data already existing?
        # If so, merge data
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
        # Else make a new file and folders and dump the data
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

    flask_login.login_user(user)  # Actually log in the user
    return redirect(url_for('dashboard'))  # Redirect to dashboard


@app.route('/')
def index():
    if flask_login.current_user.is_authenticated:  # If you're logged in, you get the dashboard
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/dashboard')
@flask_login.login_required
def dashboard():
    user = json.loads(open(os.path.join(
        'data', flask_login.current_user.get_id(), 'user.json')).read())  # Load user data
    client = requests.session()
    client.headers.update(
        {'Authorization': 'Bearer ' + user["discord_token"]["access_token"]})  # Use the saved OAuth2 token
    guilds = json.loads(client.get(
        app.config['DISCORD_API_BASE_URL'] + 'users/@me/guilds').text)  # Get all guilds the user is a member of
    ownedGuilds = []
    for guild in guilds:
        if guild['owner'] == True:
            # Filterashlib.sha256() it down to only owned guilds
            ownedGuilds.append(guild)
    return render_template('dashboard.html', username=user["username"], guilds=ownedGuilds, user=user)


@app.route('/logout')
def logout():
    flask_login.logout_user()  # Logout the user
    return redirect(url_for('index'))


@app.route('/api/user/socketiotoken')
@flask_login.login_required
def socketioToken():
    if request.args.get('sid') == None:
        abort(400)
    user = json.loads(open(os.path.join(
        'data', flask_login.current_user.get_id(), 'user.json')).read())
    token = os.urandom(64).hex()
    data = {'token': token, 'timestamp': time.time(), 'sid': request.args.get(
        'sid'), 'user': flask_login.current_user.get_id()}
    if not 'tokens' in user:
        user['tokens'] = {}

    user['tokens'][data['token']] = data
    with open(os.path.join('data', flask_login.current_user.get_id(), 'user.json'), 'w') as outfile:
        json.dump(user, outfile)
    try:
        with open(os.path.join('data', 'tokens.json'), 'r') as tokensFile:
            try:
                tokens = json.loads(tokensFile.read())
            except JSONDecodeError:
                tokens = {}
    except FileNotFoundError:
        pass
    with open(os.path.join('data', 'tokens.json'), 'w') as tokensFile:
        if tokens:
            tokens[request.args.get('sid')] = data
        else:
            tokens = {}
            tokens[request.args.get('sid')] = data
        json.dump(tokens, tokensFile)
    return jsonify(token)


@app.route('/dashboard/guild/<guild_id>')
@flask_login.login_required
def guild(guild_id):
    if guild_id.isdecimal():  # Is the ID a number?
        if checkGuild(guild_id):  # Is the bot in the guild?
            user = json.loads(open(os.path.join(
                'data', flask_login.current_user.get_id(), 'user.json')).read())  # Load user data
            if not os.path.exists(os.path.join('data', guild_id, 'guild.json')):
                os.makedirs(os.path.join(
                    'data', werkzeug.utils.secure_filename(guild_id)))
                guild = open(os.path.join('data', guild_id, 'guild.json'), 'w')
                guild.write(json.dumps({'guild_id': guild_id}))
                guild.close()
            guild = json.loads(
                open(os.path.join('data', werkzeug.utils.secure_filename(guild_id), 'guild.json')).read())
            if not guild_id in user['guilds']:
                user['guilds'].append(guild_id)
                with open(os.path.join('data', flask_login.current_user.get_id(), 'user.json'), 'w') as outfile:
                    json.dump(user, outfile)
            commands = json.load(
                open(os.path.join('staticData', 'commands.json')))
            return render_template('guild.html', guild=guild, user=user, username=user["username"], guild_id=guild_id,
                                   commands=commands, channels=getChannels(guild_id))
        else:
            return redirect(getInviteURL(guild_id))
    else:
        abort(400)  # If you're curious Acid, see here: https://mzl.la/3FEFpdR


@socket.on('updateGuildCommands')
def updateGuildCommands(data):
    token = json.load(open(os.path.join('data', 'tokens.json')))[request.sid]
    if data['token'] == token['token'] and token['timestamp'] - time.time() < 172800:
        user = json.loads(open(os.path.join(
            'data', token['user'], 'user.json')).read())
        if data['guild_id'] in user['guilds']:
            socket.emit('guildEnableCommands', {
                        "guild_id": data['guild_id'], "commands": data['enabled']}, to=botSID)
            socket.emit('guildDisableCommands', {
                        "guild_id": data['guild_id'], "commands": data['disabled']}, to=botSID)


@socket.on('getGuildDisabledCommands')
def guildDisabledCommands(data):
    token = json.load(open(os.path.join('data', 'tokens.json')))[request.sid]
    if data['token'] == token['token'] and token['timestamp'] - time.time() < 172800:
        user = json.loads(open(os.path.join(
            'data', token['user'], 'user.json')).read())
        if data['guild_id'] in user['guilds']:
            socket.emit('getGuildDisabledCommands', {
                        "sid": request.sid, "guild_id": data['guild_id']}, to=botSID)


@socket.on('sendGuildDisabledCommands')
def sendGuildDisabledCommands(data):
    if request.sid == botSID:
        socket.emit('sendGuildDisabledCommands', data, to=data['sid'])

# @socket.on('token')
# def token(data):
#     token = json.loads(open(os.path.join('data', 'tokens.json')))[request.sid]
#     user = json.loads(open(os.path.join(
#         'data', token['user'], 'user.json')).read())
#     if user['tokens'][data]['sid'] == request.sid:


# Test code
# @app.route('/dashboard/guild/<guild_id>/embed')
# @flask_login.login_required
# def embedRoute(guild_id):
#     return "OK"


# OLD CODE BELOW, PRESERVED IN CASE NEEDED IN FUTURE
# @app.route('/dashboard/guild/<guild_id>/channels/<channel_id>/msg')
# @flask_login.login_required
# def guild_msg(guild_id, channel_id):
#     msg = request.args.get('message')
#     user = json.loads(open(os.path.join(
#         'data', flask_login.current_user.get_id(), 'user.json')).read())
#     if guild_id in user['guilds']:
#         socket.emit(
#             'msg', {'message': msg, 'channel_id': channel_id, 'guild_id': guild_id})
#     return jsonify({'status': 'success', 'handover': True})


# @app.route('/dashboard/guild/<guild_id>/channels')
# @flask_login.login_required
# def guild_channels(guild_id):
#     user = json.loads(open(os.path.join(
#         'data', flask_login.current_user.get_id(), 'user.json')).read())
#     if guild_id in user['guilds']:
#         channels = getChannels(guild_id)
#         textChannels = []
#         for channel in channels:
#             if channel['type'] == 0 or channel['type'] == 5:
#                 textChannels.append(channel)
#         return render_template('channels.html', channels=textChannels, guild_id=guild_id)

#     else:
#         return redirect(getInviteURL(guild_id))


# @app.route('/dashboard/guild/<guild_id>/channels/<channel_id>')
# @flask_login.login_required
# def guild_channel(guild_id, channel_id):
#     user = json.loads(open(os.path.join(
#         'data', flask_login.current_user.get_id(), 'user.json')).read())
#     if guild_id in user['guilds']:
#         channel = getChannel(channel_id)
#         return render_template('channel.html', channel=channel, guild_id=guild_id)
#     else:
#         return redirect(getInviteURL(guild_id))


@app.route('/dashboard/admin')
@flask_login.login_required
def admin():
    user = json.loads(open(os.path.join(
        'data', flask_login.current_user.get_id(), 'user.json')).read())  # Load user data
    if user['admin'] == True:  # Is the user an admin?
        commands = json.load(open(os.path.join('staticData', 'commands.json')))
        return render_template('admin.html', user=user, username=user['username'], allGuildsLength=len(getBotGuilds()),
                               commands=commands)  # If so, render and return the admin page
    else:
        # Redirect to the normal dashboard if not
        return redirect(url_for('dashboard'))


# Requested after a succeddful invite
@app.route('/invite/callback')
def invite_callback():
    if request.args.get("guild_id").isdecimal():  # Check if the guild_id is a number
        # Redirect to the dashboard page for that guild, for a smooth user experience
        return redirect(f'/dashboard/guild/{request.args.get("guild_id")}')
    else:
        abort(400)


@app.route('/api/assets/bot/<assetID>')
def botAssets(assetID):
    return send_from_directory('botAssets', werkzeug.utils.secure_filename(assetID))


@app.route('/api/dashboard/embed', methods=["POST"])
@flask_login.login_required
def embed():
    user = json.loads(open(os.path.join(
        'data', flask_login.current_user.get_id(), 'user.json')).read())
    data = json.loads(request.form['data'])
    if data['guildID'] in user['guilds']:
        if 'thumbnail' in request.files and request.files['thumbnail'].filename != '':
            print("Thumbnail true")
            thumbnail = request.files['thumbnail']
            thumbnailID = os.urandom(32).hex() + '.' + \
                thumbnail.filename.rsplit('.', 1)[1].lower()
            thumbnailPath = os.path.join('botAssets', thumbnailID)
            thumbnail.save(thumbnailPath)
            data['thumbnail'] = url_for(
                'botAssets', assetID=thumbnailID, _external=True)
        if 'image' in request.files and request.files['image'].filename != '':
            print("Image true")
            image = request.files['image']
            imageID = os.urandom(32).hex() + '.' + \
                image.filename.rsplit('.', 1)[1].lower()
            imagePath = os.path.join('botAssets', imageID)
            image.save(imagePath)
            data['image'] = url_for(
                'botAssets', assetID=imageID, _external=True)
        if 'authorIcon' in request.files and request.files['authorIcon'].filename != '':
            print("Author icon true")
            authorIcon = request.files['authorIcon']
            authorIconID = os.urandom(
                32).hex() + '.' + authorIcon.filename.rsplit('.', 1)[1].lower()
            authorIconPath = os.path.join('botAssets', authorIconID)
            authorIcon.save(authorIconPath)
            data['authorIcon'] = url_for(
                'botAssets', assetID=authorIconID, _external=True)
        data['message-text'] = markdownify.markdownify(data['message-text'])
        socket.emit('embed', data, to=botSID)
        return "200"
    else:
        abort(403)


# Ping!
@socket.on('ping')
def pingSocket():
    socket.emit('pong')


# Send the favicon (the logo)
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'logo.png', mimetype='image/png')


@socket.on('connect')
def connection(data):
    global botSID
    if data:  # Has authdata been presented
        if data['key'] == app.config['BOT_KEY']:  # If so, is it correct?
            botSID = request.sid
        else:
            print("Bot presented incorrect auth key - rejecting")
            print(data['key'])
            return False  # Kick that nasty un-authed thingy off - yuck! LOL
    else:
        socket.emit('getToken')


@socket.on('pingBot')
def pingBot():
    if botSID:  # Do we have a connection ID for the bot?
        socket.emit('ping', to=botSID)  # Send a ping to the bot
        # Tell the requesting web browser that a ping has been sent - currently unused except for manual debugging
        socket.emit('pinged', to=request.sid)


@socket.on('pong')  # When we get a pong
def pong():
    # Send all socketio clients the bot's status
    socket.emit('botStatus', {"status": "OK"}, broadcast=True)


@socket.on('settingsChange')  # Setting changes from the web browser
def settingsChange(data):
    token = json.load(open(os.path.join('data', 'tokens.json')))[request.sid]
    if data['token'] == token['token'] and token['timestamp'] - time.time() < 172800:
        user = json.loads(open(os.path.join(
            'data', flask_login.current_user.get_id(), 'user.json')).read())
        if data['guilds_id'] in user['guilds']:
            # Send them on directly to the bot
            socket.emit('settingsChange', data, to=botSID)


@socket.on('getAllCommands')
def getAllCommands(data):
        socket.emit('getAllCommands', {"sid": request.sid},
                    to=botSID)  # Send a request for all commands to the bot, sending the requester's SID for the callback


@socket.on('getDisabledCommands')
def getAllCommands(data):
    token = json.load(open(os.path.join('data', 'tokens.json')))[request.sid]
    if data['token'] == token['token'] and token['timestamp'] - time.time() < 172800 and json.loads(open(os.path.join('data', flask_login.current_user.get_id(), 'user.json')).read())['admin']:
        socket.emit('getDisabledCommands', {"sid": request.sid},
                    to=botSID)  # Send a request for all disabled commands to the bot, sending the requester's SID for the callback


@socket.on('disabledCommands')
def disabledCommands(data):
    # When we get the data back, send it to the requester's SID
    socket.emit('disabledCommands', data, to=data['sid'])


@socket.on('enableCommand')
def enableCommand(data):
    token = json.load(open(os.path.join('data', 'tokens.json')))[request.sid]
    if data['token'] == token['token'] and token['timestamp'] - time.time() < 172800 and json.loads(open(os.path.join('data', flask_login.current_user.get_id(), 'user.json')).read())['admin']:
        # Requests a command to be enabled
        socket.emit('enableCommand', data, to=botSID)


@socket.on('allCommands')  # When we receive the list of all the commands
def allCommands(data):
    commands = {}
    for entry in data['commands']:
        if not entry['cog'] in commands:  # If we don't have the cog in the dict
            # Make a new dict key with an empty list for that cog
            commands[entry['cog']] = []
        # Add the command to its respective cog
        commands[entry['cog']].append(entry)
    # Delete commands with no cog - this includes some sort of default help command
    del commands[None]
    # Save to a file
    json.dump(commands, open(os.path.join('staticData', 'commands.json'), 'w'))
    # Emit them (currently unused)
    socket.emit('allCommands', data['commands'], to=data["sid"])


# @socket.on('getWarnings')
# def getWarnings(data):
#     socket.emit('getWarnings', {"guildID": data['guildID']}, to=botSID)

@socket.on('updateCommands')
def updateCommands(data):
    token = json.load(open(os.path.join('data', 'tokens.json')))[request.sid]
    if data['token'] == token['token'] and token['timestamp'] - time.time() < 172800 and json.loads(open(os.path.join('data', flask_login.current_user.get_id(), 'user.json')).read())['admin']:
        socket.emit('updateCommands', data, to=botSID)


if __name__ == '__main__':
    # Run it if not using flask debugger
    socket.run(app, host='0.0.0.0', port=app.config['PORT'])
