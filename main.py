import timetable
import wordplay
import telebot
from telebot import types
from oauth2client import client
import random
import datetime
import sys
import json
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

with open('bible_lemmas.txt', 'r', encoding='utf-8') as f:
    bible = f.read().split()

repeat = True
while repeat:
    try:
        timetable.auth()
    except client.HttpAccessTokenRefreshError:
        repeat = True
    else:
        repeat = False
print('> auth complete!')

token = os.environ.get("TOKEN")
bot=telebot.TeleBot(token, threaded=False)


bot.set_my_commands([
    telebot.types.BotCommand(command='start', description='приветствие'),
    telebot.types.BotCommand(command='plan', description='добавить материалы на неделю'),
    telebot.types.BotCommand(command='guests', description='списки на дату'),
    telebot.types.BotCommand(command='triggers', description='список скрытых талантов'),
    telebot.types.BotCommand(command='ping', description='(дебаг) пинг'),
    telebot.types.BotCommand(command='list', description='(дебаг) текстовое расписание'),
    telebot.types.BotCommand(command='posters', description='(дебаг) афиши'),
    telebot.types.BotCommand(command='poll', description='(дебаг) опрос участия'),
    telebot.types.BotCommand(command='forms', description='(дебаг) гугл-формы'),
])
bot.set_chat_menu_button(menu_button=types.MenuButtonCommands('commands'))

@bot.message_handler(commands=['start'])
def command_start(message):
    text = 'Привет! Я ВШЭстерёнка (⁠◕⁠ᴗ⁠◕⁠)\nНижегородские трамваи постепенно роботизируются, пристегнитесь покрепче.\n\nСписок текущих команд можно посмотреть по кнопке.'
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['triggers'])
def command_triggers(message):
    text = 'Список текущих скрытых талантов:\n⚡ реагирую на непростые\n🌸 замечаю хайку\n🌭 присоединяюсь к форсам'
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['list'])
def command_list(message):
    args = message.text.split()
    old_stdout = sys.stdout
    text = timetable.print_plans(args[1] if len(args)>1 else 'week', args[2] if len(args)>2 else None)
    sys.stdout = old_stdout
    bot.send_message(message.chat.id, text)
    
@bot.message_handler(commands=['posters'])
def command_posters(message):
    args = message.text.split()
    response = timetable.draw_plans(args[1] if len(args)>1 else 'week', args[2] if len(args)>2 else None)
    bot.send_media_group(message.chat.id, response.prepare())
    response.clear()
    
@bot.message_handler(commands=['poll'])
def command_poll(message):
    args = message.text.split()
    question, options, is_closed = timetable.poll_plans(args[1] if len(args)>1 else 'week', args[2] if len(args)>2 else None)
    bot.send_poll(
        message.chat.id, 
        question, 
        options, 
        is_anonymous=False, 
        allows_multiple_answers=True, 
        is_closed=is_closed
    )
    
@bot.message_handler(commands=['forms'])
def command_forms(message):
    args = message.text.split()    
    placeholder = bot.send_message(message.chat.id, 'Формы сейчас будут 👉👈')
    old_stdout = sys.stdout
    text, form_ids = timetable.form_plans(args[1] if len(args)>1 else 'week', args[2] if len(args)>2 else None)
    sys.stdout = old_stdout
    bot.edit_message_text(text, message.chat.id, placeholder.message_id)
    
@bot.message_handler(commands=['guests'])
def command_guests(message):
    args = message.text.split()
    old_stdout = sys.stdout
    date = datetime.date.today() + datetime.timedelta(days=2)
    date = date.strftime("%Y%m%d")
    text = timetable.get_guests(args[1] if len(args)>1 else 'day', args[2] if len(args)>2 else date)
    sys.stdout = old_stdout
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['plan'])
def command_plan(message):
    chat = str(message.chat.id)
    args = message.text.split()
    date = datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())
    expiry_date = date.strftime("%Y%m%d")
    if 'next' in args:
        date += datetime.timedelta(days=7)
    date = date.strftime("%Y%m%d")
    period = 'week'
    
    with open('current_plans.json', 'r') as f:
        current_plans = json.load(f)
    if chat in current_plans and date in current_plans[chat] and 'force' not in args:
        bot.send_message(message.chat.id, 'Неделя уже запланирована. Если хотите полностью обновить информацию, используйте аргумент force')
        return
    
    if chat not in current_plans:
        current_plans[chat] = {}
    if date not in current_plans[chat]:
        current_plans[chat][date] = {}
    
    old_stdout = sys.stdout
    text = timetable.print_plans(period, date)
    sys.stdout = old_stdout
    sent_list = bot.send_message(message.chat.id, text)
    current_plans[chat][date]['list'] = sent_list.message_id 
    try:
        bot.pin_chat_message(message.chat.id, current_plans[chat][date]['list'], disable_notification=True)
    except:
        print('! pin message error')
    
    question, options, is_closed = timetable.poll_plans(period, date)
    sent_poll = bot.send_poll(
        message.chat.id, 
        question, 
        options, 
        is_anonymous=False, 
        allows_multiple_answers=True, 
        is_closed=is_closed
    )
    current_plans[chat][date]['poll'] = sent_poll.message_id 
    
    response = timetable.draw_plans(period, date)
    sent_posters = bot.send_media_group(message.chat.id, response.prepare())
    current_plans[chat][date]['posters'] = sent_posters[0].message_id 
    response.clear()
    
    sent_forms = bot.send_message(message.chat.id, 'Формы сейчас будут 👉👈')
    old_stdout = sys.stdout
    text = timetable.form_plans(period, date)
    sys.stdout = old_stdout
    bot.edit_message_text(text, message.chat.id, sent_forms.message_id)
    current_plans[chat][date]['forms'] = sent_forms.message_id 
    
    old_plans = []
    for key in current_plans[chat]:
        if key == 'last':
            continue
        if int(key) < int(expiry_date):
            old_plans.append(key)
    for old in old_plans:
        try:
            bot.unpin_chat_message(message.chat.id, current_plans[chat][old]['list'])
        except:
            print('! unpin message error')
        current_plans[chat].pop(old)
    with open('current_plans.json', 'w') as f:
        json.dump(current_plans, f)


@bot.message_handler(commands=['ping'])
def command_ping(message):
    bot.set_message_reaction(message.chat.id, message.id, [types.ReactionTypeEmoji('👌')], is_big=False)


@bot.message_handler(commands=['send'])
def command_send(message):
    args = message.text.split()  
    chat = args[1]
    content = args[2]
    chat = os.environ.get(chat.upper()) if os.environ.get(chat.upper()) is not None else chat
    try:
        bot.send_message(chat, content, entities=[types.MessageEntity('spoiler', 0, len(content))])
    except:
        pass
    else:
        bot.set_message_reaction(message.chat.id, message.id, [types.ReactionTypeEmoji('🫡')], is_big=False)
    

def reactions(messages):
    for message in messages:
        if not message.text:
            return
        old_stdout = sys.stdout
        
        if wordplay.check_equi(message.text):
            bot.set_message_reaction(message.chat.id, message.id, [types.ReactionTypeEmoji('⚡')], is_big=False)
            
        haiku = wordplay.find_haiku(message.text)
        if haiku:
            bot.send_message(message.chat.id, haiku, reply_parameters=telebot.types.ReplyParameters(message.id))
           
        if str(message.chat.id) == os.environ.get("DEBUG_CHAT"):
            if not wordplay.check_bible(message.text, bible):
                reply = '(ни одного из этих слов нет в Библии)'
                # bot.send_message(message.chat.id, reply, reply_parameters=telebot.types.ReplyParameters(message.id))
            
        sys.stdout = old_stdout


def join_in(messages):
    with open('current_plans.json', 'r') as f:
        current_plans = json.load(f)
        
    for message in messages:
        chat = str(message.chat.id)
        content = ''
        if message.sticker is not None:
            typ = 'sticker'
            content = message.sticker.file_id
        elif message.text is not None:
            typ = 'text'
            content = message.text
        else:
            typ = 'other'
        content = content.lower()
        forbidden = ['custom_emoji', 'bot_command']
        entities = message.entities if message.entities is not None else []
        if any(map(lambda x: x.type in forbidden, entities)):
            typ = 'other'
        if chat not in current_plans:
            current_plans[chat] = {}
        if 'last' not in current_plans[chat]:
            current_plans[chat]['last'] = {'message': '', 'type': '', 'count': 0}
        last_content = current_plans[chat]['last']['message']
        last_type = current_plans[chat]['last']['type']
        if typ != 'other' and last_type == typ and last_content == content:
            current_plans[chat]['last']['count'] += 1
        else:
            current_plans[chat]['last']['message'] = content
            current_plans[chat]['last']['type'] = typ
            current_plans[chat]['last']['count'] = 1
    
    for chat in current_plans.keys():
        if 'last' in current_plans[chat] and current_plans[chat]['last']['count'] > 2:
            if current_plans[chat]['last']['type'] == 'text':
                bot.send_message(chat, current_plans[chat]['last']['message'])
            if current_plans[chat]['last']['type'] == 'sticker':
                bot.send_sticker(chat, current_plans[chat]['last']['message'])
            current_plans[chat]['last']['count'] = 0
    with open('current_plans.json', 'w') as f:
        json.dump(current_plans, f)
        

print('> bot running!')

bot.set_update_listener(reactions)  
bot.set_update_listener(join_in)    
bot.infinity_polling()