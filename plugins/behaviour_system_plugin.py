# -*- coding: utf-8 -*-
"""basic, inbuilt actions"""
from twistedbot import behaviours
from twistedbot.logbot import getlogger

log = getlogger('SYSTEM PLUGINS')


def rotate_and_circulate(user, verb, data, interface):
    """"rotate <group>" or "circulate <group>": follow signs in a group, in-order."""
    if data:
        interface.world.bot.behaviour_tree.new_command(
                    behaviours.WalkSignsBehaviour, group=data, type=verb)
    else:
        interface.world.chat.send_message("which sign group to %s?" % verb)


def go(user, verb, data, interface):
    """"go <player>" or "go <sign>": go to a player or sign"""
    world, chat = interface.world, interface.world.chat
    if data:
        split_data = data.split()
        if len(split_data) == 2 and split_data[0] == 'to':
            if split_data[1] in world.entities.players:
                msg = ("I don't know how to go to other players yet.")
                chat.send_message(msg)
        else:
            world.bot.behaviour_tree.new_command(behaviours.GoToSignBehaviour,
                                                 sign_name=data)
    else:
        interface.world.chat.send_message("go where?")


def look(user, verb, data, interface):
    """"look at <player>" or "look at me" """
    world, chat = interface.world, interface.world.chat
    new_command = world.bot.behaviour_tree.new_command

    data = data.split()
    if data[0].strip() != 'at':
        chat.send_message("look.. ..what?  look at who?")
        return
    if len(data) != 2:
        chat.send_message("look at who?")
        return
    if data[1].strip().lower() == 'me':
        new_command(behaviours.LookAtPlayerBehaviour, player='me')
    else:
        new_command(behaviours.LookAtPlayerBehaviour, player=data[1].strip())


def follow(user, verb, data, interface):
    """"follow <player>" or "follow me" """
    new_command = interface.world.bot.behaviour_tree.new_command
    data = data.strip()
    if data:
        new_command(behaviours.FollowPlayerBehaviour, player=data)
    else:
        new_command(behaviours.FollowPlayerBehaviour)


def cancel(user, verb, data, interface):
    """"cancel": cancel running actions, and do basic idle behaviours."""
    cancel_running = interface.world.bot.behaviour_tree.cancel_running
    if data.lower() == 'all':
        interface.world.chat.send_message("Cancelling all activities..")
        interface.world.bot.cancel_value = behaviours.Priorities.absolute_top
        return
#        cancel_running(behaviours.Priorities.absolute_top)
#    cancel_running(behaviours.Priorities.user_command)
    interface.world.bot.cancel_value = behaviours.Priorities.user_command


def show(user, verb, data, interface):
    """"show <sign group>" or "show <sign name>": report info on sign"""
    world = interface.world
    if data:
        sign = world.sign_waypoints.get_namepoint(data)
        if sign is not None:
            world.chat.send_message(str(sign))
            return
        sign = world.sign_waypoints.get_name_from_group(data)
        if sign is not None:
            world.chat.send_message(str(sign))
            return
        if not world.sign_waypoints.has_group(data):
            world.chat.send_message("no group named %s" % data)
            return
        for sign in world.sign_waypoints.ordered_sign_groups[data].iter():
            world.chat.send_message(str(sign))
    else:
        world.chat.send_message("show what?")


def shortcut(user, verb, data, interface):
    """"shortcut <command shortcut>": set the command shortcut (defaults to '!')"""
    data = data.strip()
    interface.world.chat.command_str = data
    interface.world.chat.send_message("Command shortcut set to: " + data)


def report(user, verb, data, interface):
    """"report": announce current behaviour"""
    interface.world.bot.behaviour_tree.announce_behaviour()


def manager(user, verb, data, interface):
    """"promote <player>", "demote <player>": grant or revoke manager status."""
    world = interface.world
    chat = interface.world.chat
    if user.lower() != world.commander.name:
        chat.send_message("NO!")
        return
    name = data.strip()
    if not data:
        chat.send_message(verb.capitalize() + ' who?')
        return
    if verb == 'promote':
        if name in world.entities.players:
            chat.send_message("Ok, {} is the boss of me.".format(name))
        else:
            msg = "Ok, {} is the boss of me.. ..but I don't see 'em."
            chat.send_message(msg.format(name))
        world.managers.add(name)
    elif verb == 'demote':
        if name in world.managers:
            world.managers.remove(name)
            chat.send_message("{}, You're Fired!".format(name))
        else:
            msg = "Psh.  {}'s not the boss of me, anyways.".format(name)
            chat.send_message(msg)

verbs = {
    'rotate': rotate_and_circulate,
    'circulate': rotate_and_circulate,
    'go': go,
    'look': look,
    'follow': follow,
    'cancel': cancel,
    'report': report,
    'stop': cancel,
    'show': show,
    'shortcut': shortcut,
    'promote': manager,
    'demote': manager,
    }