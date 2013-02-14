# Bot/Proxy for Minecraft
Twitter [@lukleh](https://twitter.com/lukleh "@lukleh")
#### Technical info
- Support for 1.4.7 protocol version 51
- Running under [PyPy](http://pypy.org/ "PyPy")
- Clean [flake8](http://pypi.python.org/pypi/flake8/ "flake8") with long lines
- Optional (mandatory for proxy mode) [PyCrypto](https://www.dlitz.net/software/pycrypto/ "PyCrypto") dependency if you want the datastream to be encrypted. Configurable in config.
- pywin32 dependency under Windows in proxy mode - not supplied.
- Rest of the dependencies is included in "libs" directory.


## Bot
#### Features
- Client side artificial player for Minecraft that runs on vanilla server in offline mode. No modification on server/client side needed.
- Basic pathfinding
- Solid block awareness
- Avoiding lava, web and cactus
- Reasonable handeling of vines, ladders and water
- No active interaction with the world. That is no digging, placing blocks, open/close doors, etc.
- Use signs to set up points to rotate  -> details below
- Configure using command line arguments or modifying twistedbot/config.py
- In the idle state bot just stares at you, turning his head and body.

#### Usage
By default connects to localhost

	pypy bot.py 

Possible flags

	pypy bot.py -h

#### In game commands
If your username (commander) is set, then you can use chat to send commands to bot.

- "look at me" stands still and looks at you
- "rotate 'group'" rotates (after the end, goes back to the beginning) between signs -> details below
- "circulate 'group'" circulates (at the end, goes backward towards the beginnings) between signs -> details below
- "go 'name'" go to specific waypoint identified by name, or if name is group and order separated with space
- "show 'name'" show in chat waypoint, group or waypoints in group
- "follow me" bot starts following you
- "cancel" cancel current activity

#### Sign waypoints
Use signs as a waypoints. When you want the sign to be part of waypoints that bot can travel between do the following, all without quotes:

- place sign
- line 1: 'waypoint' 
- line 2: Name of waypoint
- line 3: Groupname (Optional): Add this waypoint to a group
- line 4: Number - Determines the order for the bot to visit the sign, if it's in a group

## Proxy
- Intercepts network traffic between client and server, usefull for debugging and figuring out how Minecraft works.
- If you are runnig server, proxy and client on the same machine, have quad core.
- Keep in mind that thanks to the encryption, proxy has to first decrypt and then encrypt again. This may cause a noticeable delay.

#### Usage
To run with defaults, server is localhost:25565 and proxy is listening on localhost:25566. Then connect your client to localhost:25566.

	pypy proxy.py
	
When you close proxy, it prints packet statistics before exit.

Possible flags

	pypy proxy.py -h

To make your own filter, look in twistedbot.proxy_processors.default for an example.
