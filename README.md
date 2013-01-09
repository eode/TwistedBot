# Bot/Proxy for Minecraft
- Support for 1.4.7 protocol version 51
- Running under [PyPy](http://pypy.org/ "PyPy")
- flake8 clean with long lines
- Optional (mandatory for proxy mode) [PyCrypto](https://www.dlitz.net/software/pycrypto/ "PyCrypto") dependency if you want the datastream to be encrypted. Also configurable in config.
- Twisted needs pywin32 dependency under Windows in proxy mode.
- Rest of the dependencies is included in "libs" directory.


## Bot
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

#### Possible flags
	pypy bot.py -h

#### In game commands
If your username (commander) is set, then you can use chat to send commands to bot.

- "look at me" stands still and looks at you
- "rotate 'group'" rotates (after the end, goes back to the beginning) between signs -> details below
- "circulate 'group'" circulates (at the end, goes backward towards the beginnings) between signs -> details below
- "go 'name'" go to specific waypoint identified by name, or if name is group and order separated with space
- "show 'wp'" show in chat waypoint, group or waypoint in group with name 'wp'
- "follow me" bot starts following you
- "cancel" cancel current activity

#### Sign waypoints
Use signs as a waypoints. When you want the sign to be part of waypoints that bot can travel between do the following, all without quotes:
- place sign
- first line: 'waypoint' 
- second line:
-- number, for example '1', '2' or '3.5'  It will be used as an order of how to sort the waypoints
-- or a name, in that case waypoint can be addressed directly
- third line: groupname, if given number on line 2, this name groups waypoints
- fourth line: name, if number and groupname given. same function as name in line 2

## Proxy
- Intercepts network traffic between client and server, usefull for debugging and figuring out how Minecraft works
- If you are runnig server, proxy and client on the same machine, have quad core
- Keep in mind that thanks to the encryption, proxy has to first decrypt and then encrypt again. There is a noticeable delay

#### Usage
To run with defaults, server is localhost:25565 and proxy is listening on localhost:25566. Then connect your client to localhost:25566.

	pypy proxy.py
	
When you close proxy, it prints packet statistics before exit

#### Possible flags
	pypy proxy.py -h

To make your own filter, look in twistedbot.proxy_processors.default for an example.

##### Other places
Twitter [@lukleh](https://twitter.com/lukleh "@lukleh")
