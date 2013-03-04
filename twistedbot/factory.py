
from collections import deque

from twisted.internet.protocol import ReconnectingClientFactory, Protocol
from twisted.internet import reactor

import config
import logbot
import proxy_processors.default
import utils
from packets import parse_packets, make_packet, packets_by_name, Container
from proxy_processors.default import process_packets as packet_printout

proxy_processors.default.ignore_packets = []
proxy_processors.default.filter_packets = []

log = logbot.getlogger("FACTORY")

# Packet debugging enabled by default if debugging is on.
log_packet_types = dict([(x, False) for x in xrange(256)])
# Disable packet debugging for these packet types:
enabled_packets = []

for pack in enabled_packets:
    log_packet_types[pack] = True


class MineCraftProtocol(Protocol):
    def __init__(self, world):
        self.world = world
        self.world.protocol = self
        self.leftover = ""
        self.encryption_on = False
        self.packets = deque()

        self.router = {
            0x00: self.p_ping,
            0x01: self.p_login,
            # 0x02: handshake to server
            0x03: self.p_chat,
            0x04: self.p_time,
            0x05: self.p_entity_equipment,
            0x06: self.p_spawn,
            # 0x07: self.p_use_entity (client to server),
            0x08: self.p_health,
            0x09: self.p_respawn,
            0x0d: self.p_location,
            0x10: self.p_held_item_change,
            0x11: self.p_use_bed,
            0x12: self.p_animate,
            0x14: self.p_player,
            0x15: self.p_dropped_item,
            0x16: self.p_collect,
            0x17: self.p_vehicle,
            0x18: self.p_mob,
            0x19: self.p_spawn_painting,
            0x1a: self.p_experience_orb,
            0x1c: self.p_entity_velocity,
            0x1d: self.p_entity_destroy,
            0x1f: self.p_entity_move,
            0x20: self.p_entity_look,
            0x21: self.p_entity_move_look,
            0x22: self.p_entity_teleport,
            0x23: self.p_entity_head_look,
            0x26: self.p_entity_status,
            0x27: self.p_entity_attach,
            0x28: self.p_entity_metadata,
            0x29: self.p_entity_effect,
            0x2a: self.p_entity_remove_effect,
            0x2b: self.p_levelup,
            0x33: self.p_chunk,
            0x34: self.p_multi_block_change,
            0x35: self.p_block_change,
            0x36: self.p_block_action,
            0x37: self.p_block_break_animation,
            0x38: self.p_bulk_chunk,
            0x3c: self.p_explosion,
            0x3d: self.p_sound,
            0x3e: self.p_named_sound,
            0x46: self.p_state,
            0x47: self.p_spawn_global_entity,
            0x64: self.p_open_window,
            0x65: self.p_close_window,
            0x66: self.p_click_window,
            0x67: self.p_set_slot,
            0x68: self.p_set_window_items,
            0x67: self.p_window_slot,
            0x6a: self.p_confirm_transaction,
            0x82: self.p_sign,
            0x83: self.p_item_data,
            0x84: self.p_update_tile,
            0xc8: self.p_stats,
            0xc9: self.p_players,
            0xca: self.p_abilities,
            0xcb: self.p_tab_complete,
            0xfa: self.p_plugin_message,
            0xfc: self.p_encryption_key_response,
            0xfd: self.p_encryption_key_request,
            0xff: self.p_error,
        }

    def connectionMade(self):
        self.world.connection_made()
        log.msg("sending HANDSHAKE")
        self.send_packet("handshake", {"protocol": config.PROTOCOL_VERSION,
                                       "username": config.USERNAME,
                                       "server_host": config.SERVER_HOST,
                                       "server_port": config.SERVER_PORT})

    def connectionLost(self, reason):
        self.packets = deque()
        self.world.on_connection_lost()

    def sendData(self, bytestream):
        if self.encryption_on:
            bytestream = self.cipher.encrypt(bytestream)
        self.transport.write(bytestream)

    def dataReceived(self, bytestream):
        try:
            self.parse_stream(bytestream)
        except:
            logbot.exit_on_error()

    def parse_stream(self, bytestream):
        if self.encryption_on:
            bytestream = self.decipher.decrypt(bytestream)
        parsed_packets, self.leftover = parse_packets(
            self.leftover + bytestream)
        if config.DEBUG:
            packet_printout("SERVER", parsed_packets, self.encryption_on,
                            self.leftover, log_packet_types)
        self.packets.extend(parsed_packets)
        self.packet_iter(self.packets)

    def send_packet(self, name, payload):
        p = make_packet(name, payload)
        if config.DEBUG:
            packet_printout("CLIENT",
                            [(packets_by_name[name], Container(**payload))],
                            types=log_packet_types)
        self.sendData(p)

    def packet_iter(self, ipackets):
        while ipackets:
            packet = ipackets.popleft()
            self.process_packet(packet)

    def process_packet(self, packet):
        pid = packet[0]
        payload = packet[1]
        f = self.router.get(pid, None)
        if f is not None:
            f(payload)
        else:
            log.msg("Unknown packet %d" % pid)
            reactor.stop()

    def p_ping(self, c):
        pid = c.pid
        self.send_packet("keep alive", {"pid": pid})

    def p_login(self, c):
        msg = ("LOGIN DATA eid %s level type: %s, game_mode: %s, "
               "dimension: %s, difficulty: %s, max players: %s")
        log.msg(msg % (c.eid, c.level_type, c.game_mode, c.dimension,
                        c.difficulty, c.players))
        self.world.on_login(bot_eid=c.eid, game_mode=c.game_mode,
                            dimension=c.dimension, difficulty=c.difficulty)
        locale_data = {'locale': 'en_GB',
                       'view_distance': 2,
                       'chat_flags': 0,
                       'difficulty': 0,
                       'show_cape': False}
        utils.do_now(self.send_packet, "locale view distance", locale_data)

    def p_chat(self, c):
        self.world.chat.on_chat_message(c.message)

    def p_time(self, c):
        # c is dict-like and has members c.age_of_world and c.daytime
        self.world.on_time_update(**c)

    def p_entity_equipment(self, c):
        self.world.on_entity_equipment(**c)

    def p_spawn(self, c):
        log.msg("SPAWN POSITION %s %s %s" % (c.x, c.y, c.z))
        self.world.on_spawn_position(c.x, c.y, c.z)

    def p_use_entity(self, c):
        log.msg("'use entity' received fom server: %s" % str(c))

    def p_health(self, c):
        self.world.to_gui('health', c)
        self.world.bot.on_health_update(c.hp, c.fp, c.saturation)

    def p_respawn(self, c):
        log.msg("RESPAWN received")
        self.world.on_respawn(game_mode=c.game_mode, dimension=c.dimension,
                              difficulty=c.difficulty)

    def p_location(self, c):
        log.msg("received LOCATION X:%f Y:%f Z:%f STANCE:%f GROUNDED:%s" %
                (c.position.x, c.position.y, c.position.z,
                 c.position.stance, c.grounded.grounded))
        self.world.to_gui('location', c)
        c.position.y, c.position.stance = c.position.stance, c.position.y
        self.send_packet("player position&look", c)
        self.world.bot.on_new_location({"x": c.position.x,
                                        "y": c.position.y,
                                        "z": c.position.z,
                                        "stance": c.position.stance,
                                        "grounded": c.grounded.grounded,
                                        "yaw": c.orientation.yaw,
                                        "pitch": c.orientation.pitch})

    def p_held_item_change(self, c):
#TODO This (held_item_change)!!
        pass

    def p_use_bed(self, c):
        """
        if ever will use bed, then deal with it.
        possibly also if commander uses bed.
        """
        pass

    def p_animate(self, c):
        # Ignored from server
#TODO this is two way, client uses only value 1 (swing arm). Probably needed.
        pass

    def p_player(self, c):
        self.world.entities.on_new_player(eid=c.eid, username=c.username,
                                          held_item=c.item, yaw=c.yaw,
                                          pitch=c.pitch, x=c.x, y=c.y, z=c.z)

    def p_dropped_item(self, c):
        self.world.entities.on_new_dropped_item(eid=c.eid, slotdata=c.slotdata, x=c.x,
                                                y=c.y, z=c.z, yaw=c.yaw,
                                                pitch=c.pitch, roll=c.roll)

    def p_collect(self, c):
        """ can be safely ignored, for animation purposes only """
        pass

    def p_vehicle(self, c):
        vel = {"x": c.velocity.x,
               "y": c.velocity.y,
               "z": c.velocity.z} if c.object_data > 0 else None
        self.world.entities.on_new_vehicle(eid=c.eid, etype=c.type,
                                           x=c.x, y=c.y, z=c.z,
                                           object_data=c.object_data,
                                           velocity=vel)

    def p_mob(self, c):
        self.world.entities.on_new_mob(eid=c.eid, etype=c.type, x=c.x, y=c.y,
                                       z=c.z, yaw=c.yaw, pitch=c.pitch,
                                       head_yaw=c.head_yaw,
                                       velocity_x=c.velocity_x,
                                       velocity_y=c.velocity_y,
                                       velocity_z=c.velocity_z,
                                       metadata=c.metadata)

    def p_spawn_painting(self, c):
        self.world.entities.on_new_painting(eid=c.eid, x=c.x, y=c.y, z=c.z, title=c.title)

    def p_experience_orb(self, c):
        self.world.entities.on_new_experience_orb(eid=c.eid, count=c.count, x=c.x, y=c.y, z=c.z)

    def p_entity_velocity(self, c):
        self.world.entities.on_velocity(c.eid, c.dx, c.dy, c.dz)

    def p_entity_destroy(self, c):
        self.world.entities.on_destroy(c.eids)

    def p_entity_move(self, c):
        self.world.entities.on_move(c.eid, c.dx, c.dy, c.dz)

    def p_entity_look(self, c):
        self.world.entities.on_look(c.eid, c.yaw, c.pitch)

    def p_entity_move_look(self, c):
        self.world.entities.on_move_look(c.eid, c.dx, c.dy, c.dz, c.yaw, c.pitch)

    def p_entity_teleport(self, c):
        self.world.entities.on_teleport(c.eid, c.x, c.y, c.z, c.yaw, c.pitch)

    def p_entity_head_look(self, c):
        self.world.entities.on_head_look(c.eid, c.yaw)

    def p_entity_status(self, c):
        self.world.entities.on_status(c.eid, c.status)

    def p_entity_attach(self, c):
        self.world.entities.on_attach(c.eid, c.vid)

    def p_entity_metadata(self, c):
        self.world.entities.on_metadata(c.eid, c.metadata)

    def p_entity_effect(self, c):
        #TODO pass for now
        pass

    def p_entity_remove_effect(self, c):
        #TODO pass for now
        pass

    def p_levelup(self, c):
        self.world.bot.on_update_experience(experience_bar=c.current, level=c.level, total_experience=c.total)

    def p_chunk(self, c):
        self.world.grid.on_load_chunk(c.x, c.z, c.continuous, c.primary_bitmap,
                                      c.add_bitmap, c.data.decode('zlib'))

    def p_multi_block_change(self, c):
        self.world.grid.on_multi_block_change(c.x, c.z, c.blocks)

    def p_block_change(self, c):
        self.world.grid.on_block_change(c.x, c.y, c.z, c.type, c.meta)

    def p_block_action(self, c):
        """
        implement if necessary according to http://wiki.vg/Block_Actions
        """
        pass

    def p_block_break_animation(self, c):
        """ no need for this now """
        pass

    def p_bulk_chunk(self, c):
        self.world.grid.on_load_bulk_chunk(c.meta, c.data.decode('zlib'), c.light_data)

    def p_explosion(self, c):
        self.world.grid.on_explosion(c.x, c.y, c.z, c.records)
        log.msg("Explosion at %f %f %f radius %f blocks affected %d" %
                (c.x, c.y, c.z, c.radius, c.count))

    def p_sound(self, c):
        pass

    def p_named_sound(self, c):
        pass

    def p_state(self, c):
        pass

    def p_thunderbolt(self, c):
        pass

    def p_window_slot(self, c):
        pass

    def p_inventory(self, c):
        pass

    def p_sign(self, c):
        self.world.sign_waypoints.on_new_sign(**c)

    def p_item_data(self, c):
        """ data for map item """
        pass

    def p_update_tile(self, c):
        pass
        #log.msg('Tile entity %s' % str(c))

    def p_stats(self, c):
        self.world.stats.on_update(c.sid, c.count)

    def p_players(self, c):
        if c.online:
            self.world.players[c.name] = c.ping
        else:
            try:
                del self.world.players[c.name]
            except KeyError:
                pass

    def p_abilities(self, c):
        # TODO ignore now now
        pass

    def p_tab_complete(self, c):
        # ignore
        pass

    def p_plugin_message(self, c):
        # ignore
        pass

    def p_encryption_key_response(self, c):
        self.encryption_on = True
        self.send_packet("client statuses", {"status": 0})

    def p_encryption_key_request(self, c):
        if config.USE_ENCRYPTION:
            try:
                import encryption
                key16 = encryption.get_random_bytes()
                self.cipher = encryption.make_aes(key16, key16)
                self.decipher = encryption.make_aes(key16, key16)
                public_key = encryption.load_pubkey(c.public_key)
                enc_shared_sercet = encryption.encrypt(key16, public_key)
                enc_4bytes = encryption.encrypt(c.verify_token, public_key)
                self.send_packet(
                    "encryption key response",
                    {"shared_length": len(enc_shared_sercet),
                     "shared_secret": enc_shared_sercet,
                     "token_length": len(enc_4bytes),
                     "token_secret": enc_4bytes})
            except ImportError:
                log.msg('PyCrypto not installed, skipping encryption.')
                self.send_packet("client statuses", {"status": 0})
        else:
            log.msg('USE_ENCRYPTION is False, skipping encryption.')
            self.send_packet("client statuses", {"status": 0})

    def p_error(self, c):
        log.msg('received error packet')
        msg = 'Server kicked me out with message "%s"' % c.message
        self.world.shutdown_reason = msg
        reactor.stop()


class MineCraftFactory(ReconnectingClientFactory):
    def __init__(self, world):
        self.world = world
        self.world.factory = self
        self.maxDelay = config.CONNECTION_MAX_DELAY
        self.initialDelay = config.CONNECTION_INITIAL_DELAY
        self.delay = self.initialDelay
        self.log_connection_lost = True

    def startedConnecting(self, connector):
        log.msg('Started connecting...')

    def buildProtocol(self, addr):
        log.msg('Connected!')
        if self.delay > self.initialDelay:
            log.msg('Resetting reconnection delay')
            self.resetDelay()
        protocol = MineCraftProtocol(self.world)
        protocol.factory = self
        return protocol

    def clientConnectionLost(self, connector, unused_reason):
        if self.log_connection_lost:
            log.msg('Connection lost, reason:', unused_reason.getErrorMessage())
        ReconnectingClientFactory.clientConnectionLost(self, connector, unused_reason)

    def clientConnectionFailed(self, connector, reason):
        log.msg('Connection failed, reason:', reason.getErrorMessage())
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    def shut_down(self, reason=''):
        """Shutdown, logging a reason as to why shutdown was called.  This is
        what should be called from within the thread for a clean shutdown."""
        reason = reason if reason else '(no reason given)'
        log.msg("Shutting Down")
        self.world.shutdown_reason = reason
        self.log_connection_lost = False
        reactor.stop()
