# -*- coding: utf-8 -*-
"""
Created on Tue Feb  5 19:06:35 2013

@author: silver
"""
from twistedbot import behaviours
from twistedbot.logbot import getlogger

log = getlogger('SYSTEM PLUGINS')


def rotate_and_circulate(user, verb, data, context):
        if data:
            context['world'].bot.behaviour_tree.new_command(
                        behaviours.WalkSignsBehaviour, group=data, type=verb)
        else:
            context['chat'].send_message("which sign group to %s?" % verb)


def go(user, verb, data, context):
    world, chat = context['world'], context['chat']
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
        context['chat'].send_message("go where?")


def look(user, verb, data, context):
    world, chat = context['world'], context['chat']
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


def follow(user, verb, data, context):
    new_command = context['world'].bot.behaviour_tree.new_command
    data = data.strip()
    if data:
        new_command(behaviours.FollowPlayerBehaviour, player=data)
    else:
        new_command(behaviours.FollowPlayerBehaviour)


def cancel(user, verb, data, context):
    cancel_running = context['world'].bot.behaviour_tree.cancel_running
    if data.lower() == 'all':
        context['chat'].send_message("Cancelling all activities..")
        context['world'].bot.cancel_value = behaviours.Priorities.absolute_top
        return
#        cancel_running(behaviours.Priorities.absolute_top)
#    cancel_running(behaviours.Priorities.user_command)
    context['world'].bot.cancel_value = behaviours.Priorities.user_command


def show(user, verb, data, context):
    if data:
        sign = context['world'].sign_waypoints.get_namepoint(data)
        if sign is not None:
            context['chat'].send_message(str(sign))
            return
        sign = context['world'].sign_waypoints.get_name_from_group(data)
        if sign is not None:
            context['chat'].send_message(str(sign))
            return
        if not context['world'].sign_waypoints.has_group(data):
            context['chat'].send_message("no group named %s" % data)
            return
        for sign in context['world'].sign_waypoints.ordered_sign_groups[data].iter():
            context['chat'].send_message(str(sign))
    else:
        context['chat'].send_message("show what?")


def shortcut(user, verb, data, context):
    data = data.strip()
    context['chat'].command_str = data
    context['chat'].send_message("Command shortcut set to: " + data)


def report(user, verb, data, context):
    context['world'].bot.behaviour_tree.announce_behaviour()


def py_eval(user, verb, data, context):
    world, chat = context['world'], context['chat']
    try:
        val = str(eval(data.strip()))
    except Exception, e:
        log.err()
        val = "Exception: " + str(type(e))
    # chat will messages if they contain specific characters.
    val = val.replace('<', '*').replace('>', '*').replace('|', '~')
    chat.send_message(val)

def manager(user, verb, data, context):
    """Promote and demote players to/from manager status."""
    world = context['world']
    chat = context['chat']
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
    'eval': py_eval,
    'promote': manager,
    'demote': manager,
    }