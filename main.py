import timetable
import wordplay
import telebot
from telebot import types
import datetime
import sys
import json
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

token = os.environ.get("TOKEN")
bot=telebot.TeleBot(token, threaded=False)

bot.set_my_commands([
    telebot.types.BotCommand(command='start', description='приветствие'),
    telebot.types.BotCommand(command='plan', description='добавить материалы на неделю'),
    telebot.types.BotCommand(command='update', description='обновить материалы на неделю'),
    telebot.types.BotCommand(command='triggers', description='список скрытых талантов'),
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
    text = 'Список текущих скрытых талантов:\n⚡ реагирую на непростые\n🌸 реагирую на хайку'
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
    if chat in current_plans and date in current_plans[chat]:
        bot.send_message(message.chat.id, 'Неделя уже запланирована. Может, хотите запустить /update?')
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
    bot.pin_chat_message(message.chat.id, current_plans[chat][date]['list'], disable_notification=True)
    
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
    text, form_ids = timetable.form_plans(period, date)
    sys.stdout = old_stdout
    bot.edit_message_text(text, message.chat.id, sent_forms.message_id)
    current_plans[chat][date]['forms'] = sent_forms.message_id 
    current_plans[chat][date]['form_ids'] = form_ids
    
    old_plans = []
    for key in current_plans[chat]:
        if int(key) < int(expiry_date):
            old_plans.append(key)
    for old in old_plans:
        try:
            bot.unpin_chat_message(message.chat.id, current_plans[chat][old]['list'])
        except:
            pass
        current_plans[chat].pop(old)
    with open('current_plans.json', 'w') as f:
        json.dump(current_plans, f)

@bot.message_handler(commands=['update'])
def command_update(message):
    chat = str(message.chat.id)
    args = message.text.split()
    date = datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())
    if 'next' in args:
        date += datetime.timedelta(days=7)
    date = date.strftime("%Y%m%d")
    period = 'week'
    
    with open('current_plans.json', 'r') as f:
        current_plans = json.load(f)
    if chat not in current_plans or date not in current_plans[chat]:
        bot.send_message(message.chat.id, 'Неделя ещё не запланирована. Может, хотите запустить /plan?')
        return
        
    old_stdout = sys.stdout
    text = timetable.print_plans(period, date)
    sys.stdout = old_stdout
    if 'global' in args:
        bot.unpin_chat_message(message.chat.id, current_plans[chat][date]['list'])
        sent_list = bot.send_message(message.chat.id, text)
        current_plans[chat][date]['list'] = sent_list.message_id 
        bot.pin_chat_message(message.chat.id, current_plans[chat][date]['list'], disable_notification=True)
    else:
        try:
            bot.edit_message_text(text, message.chat.id, current_plans[chat][date]['list'])
            bot.send_message(message.chat.id, 'Обновлено.', 
                reply_parameters=telebot.types.ReplyParameters(current_plans[chat][date]['list']))
        except:
            bot.send_message(message.chat.id, 'Информация актуальна', 
                reply_parameters=telebot.types.ReplyParameters(current_plans[chat][date]['list']))
    
    if 'global' in args:
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
    
    if 'global' in args:
        sent_forms = bot.send_message(message.chat.id, 'Формы сейчас будут 👉👈')
        old_stdout = sys.stdout
        text, form_ids = timetable.form_plans(period, date)
        sys.stdout = old_stdout
        bot.edit_message_text(text, message.chat.id, sent_forms.message_id)
        current_plans[chat][date]['forms'] = sent_forms.message_id 
        current_plans[chat][date]['form_ids'] = form_ids
    else:
        timetable.update_forms(current_plans[chat][date]['form_ids'])
        bot.send_message(message.chat.id, 'Обновлено (на всякий случай, как и афиши)', 
                reply_parameters=telebot.types.ReplyParameters(current_plans[chat][date]['forms']))
    
    with open('current_plans.json', 'w') as f:
        json.dump(current_plans, f)

def react_ring(messages):
    for message in messages:
        if not message.text:
            return
        old_stdout = sys.stdout
        if wordplay.check_equi(message.text):
            bot.set_message_reaction(message.chat.id, message.id, [types.ReactionTypeEmoji('⚡')], is_big=False)
        haiku = wordplay.find_haiku(message.text)
        if haiku:
            bot.send_message(message.chat.id, haiku, reply_parameters=telebot.types.ReplyParameters(message.id))
        sys.stdout = old_stdout


print('> bot running!')

bot.set_update_listener(react_ring)    
bot.infinity_polling()