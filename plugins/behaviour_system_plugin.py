# -*- coding: utf-8 -*-
"""
Created on Tue Feb  5 19:06:35 2013

@author: silver
"""
from twistedbot import behaviours

def rotate_and_circulate(data, context):
        if data:
            context['world'].bot.behaviour_tree.new_command(
                        behaviours.WalkSignsBehaviour, group=data, type=verb)
        else:
            context['chat'].send_chat_message("which sign group to %s?" % verb)

def go(data, context):
    if data:
        context['world'].bot.behaviour_tree.new_command(
                                behaviours.GoToSignBehaviour, sign_name=data)
    else:
        context['chat'].send_chat_message("go where?")

def look(data, context):
    if data == "at me":
        new_command = context['world'].bot.behaviour_tree.new_command
        new_command(behaviours.LookAtPlayerBehaviour)
    else:
        context['chat'].send_chat_message("look at what?")

def follow(data, context):
    new_command = context['world'].bot.behaviour_tree.new_command
    new_command(behaviours.FollowPlayerBehaviour)

def cancel(data, context):
    context['world'].bot.behaviour_tree.cancel_running()

def show(data, context):
    if data:
        sign = context['world'].sign_waypoints.get_namepoint(data)
        if sign is not None:
            context['chat'].send_chat_message(str(sign))
            return
        sign = context['world'].sign_waypoints.get_name_from_group(data)
        if sign is not None:
            context['chat'].send_chat_message(str(sign))
            return
        if not context['world'].sign_waypoints.has_group(data):
            context['chat'].send_chat_message("no group named %s" % data)
            return
        for sign in context['world'].sign_waypoints.ordered_sign_groups[data].iter():
            context['chat'].send_chat_message(str(sign))
    else:
        context['chat'].send_chat_message("show what?")


verbs = {
    'rotate': rotate_and_circulate,
    'circulate': rotate_and_circulate,
    'go': go,
    'look': look,
    'follow': follow,
    'cancel': cancel,
    'show': show,
    }