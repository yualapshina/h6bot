import calendar_api
import equirhythmic
import telebot
from telebot import types
import sys
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

token = os.environ.get("TOKEN")
bot=telebot.TeleBot(token, threaded=False)

bot.set_my_commands([
    telebot.types.BotCommand(command='start', description='приветствие'),
    telebot.types.BotCommand(command='print', description='текстовое расписание на текущую неделю'),
    telebot.types.BotCommand(command='draw', description='афиши на текущую неделю'),
    telebot.types.BotCommand(command='triggers', description='список скрытых талантов'),
])
bot.set_chat_menu_button(menu_button=types.MenuButtonCommands('commands'))

@bot.message_handler(commands=['start'])
def command_start(message):
    text = 'Привет! Я ВШЭстерёнка (⁠◕⁠ᴗ⁠◕⁠)\n\nСуществую, чтобы автоматизировать однообразные задачи и локальные шутки (идеи активно принимаются).\nСписок текущих команд можно посмотреть по кнопке.'
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['triggers'])
def command_triggers(message):
    text = 'Список текущих скрытых талантов:\n> реагирую на эквиритмики "обручального кольца"'
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['print'])
def command_print(message):
    args = message.text.split()
    old_stdout = sys.stdout
    text = calendar_api.print_plans(args[1] if len(args)>1 else 'week', args[2] if len(args)>2 else None)
    sys.stdout = old_stdout
    bot.send_message(message.chat.id, text)
    
@bot.message_handler(commands=['draw'])
def command_draw(message):
    args = message.text.split()
    response = calendar_api.draw_plans(args[1] if len(args)>1 else 'week', args[2] if len(args)>2 else None)
    bot.send_media_group(message.chat.id, response.prepare())
    response.clear()

def react_ring(messages):
    for message in messages:
        old_stdout = sys.stdout
        if equirhythmic.check_phrase(message.text):
            bot.set_message_reaction(message.chat.id, message.id, [types.ReactionTypeEmoji('⚡')], is_big=False)
        sys.stdout = old_stdout

print('> bot running!')

bot.set_update_listener(react_ring)    
bot.infinity_polling()