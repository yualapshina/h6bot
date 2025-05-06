from io import StringIO
import shutil
import os
import sys
import telebot
import datetime
from dateutil.relativedelta import relativedelta
from PIL import Image, ImageDraw, ImageFont
from httplib2 import Http
from oauth2client import client, file, tools
from apiclient import discovery
from googleapiclient import sample_tools
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

weekdays_short = {
    0: 'пн', 1: 'вт', 2: 'ср', 3: 'чт', 4: 'пт', 5: 'сб', 6: 'вск',
}
weekdays_long = {
    0: 'понедельник', 1: 'вторник', 2: 'среда', 3: 'четверг', 4: 'пятница', 5: 'суббота', 6: 'воскресенье',
}
months_nom = {
    1: 'январь', 2: 'февраль', 3: 'март', 4: 'апрель', 5: 'май', 6: 'июнь', 
    7: 'июль', 8: 'август', 9: 'сентябрь', 10: 'октябрь', 11: 'ноябрь', 12: 'декабрь'
}
months_gen = {
    1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля', 5: 'мая', 6: 'июня', 
    7: 'июля', 8: 'августа', 9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
}
colors_synch = ['5', '6', '11']
colors_club = ['1', '2', '3', '7', '10']

        
class ImageResponse:
    def __init__(self):
        self.prefix = 'static/' + str(datetime.datetime.now().timestamp()) + '/'
        os.mkdir(self.prefix)
        self.count = 0
        self.caption = None
        
    def set_caption(self, caption):
        self.caption = caption        

    def get_caption(self, i):
        return self.caption if not i else None
    
    def add(self, img):
        img.save(self.prefix + str(self.count) + '.png')        
        self.count += 1
        
    def prepare(self):
        self.media = []
        self.files = []
        for i in range(self.count):
            f = open(self.prefix + str(i) + '.png', 'rb')
            self.files.append(f)
            self.media.append(telebot.types.InputMediaPhoto(f, self.get_caption(i)))
        return self.media
        
    def clear(self):
        for f in self.files:
            f.close()
        shutil.rmtree(self.prefix)
            

def auth():
    SCOPES = [
        "https://www.googleapis.com/auth/forms.body",
        "https://www.googleapis.com/auth/drive.file"
    ]
    DISCOVERY_DOC = "https://forms.googleapis.com/$discovery/rest?version=v1"
    store = file.Storage("token.json")
    try:
        creds = store.get()
    except:
        creds = None
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets("client_secrets.json", SCOPES)
        creds = tools.run_flow(flow, store)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    forms = discovery.build(
        "forms",
        "v1",
        http=creds.authorize(Http()),
        discoveryServiceUrl=DISCOVERY_DOC,
        static_discovery=False,
    )
    drive = discovery.build("drive", "v3", credentials=creds)
    tempform = forms.forms().create(body={
        'info': {
                    'title': 'tempform',
                    'documentTitle': f'tempform ({datetime.datetime.now().strftime('%Y%m%d %H:%M:%S')})'
                }
    }).execute()
    drive.files().delete(fileId=tempform['formId']).execute()
    
    calendar, flags = sample_tools.init(
        sys.argv,
        "calendar",
        "v3",
        __doc__,
        __file__,
        scope="https://www.googleapis.com/auth/calendar.readonly",
    )
    calendar_id = os.environ.get("CALENDAR")
    calendar.events().list(calendarId=calendar_id).execute()


def get_services():
    DISCOVERY_DOC = "https://forms.googleapis.com/$discovery/rest?version=v1"
    creds = file.Storage("token.json").get()
    forms = discovery.build(
        "forms",
        "v1",
        http=creds.authorize(Http()),
        discoveryServiceUrl=DISCOVERY_DOC,
        static_discovery=False,
    )
    drive = discovery.build("drive", "v3", credentials=creds)
    calendar, flags = sample_tools.init(
        sys.argv,
        "calendar",
        "v3",
        __doc__,
        __file__,
        scope="https://www.googleapis.com/auth/calendar.readonly",
    )
    return forms, drive, calendar


def parse_dates(period, datestr):
    if datestr:
        queryday = datetime.datetime.strptime(datestr, "%Y%m%d")
    else:
        queryday = datetime.date.today()
    
    if period == 'day':
        date_start = queryday
        date_end = date_start + datetime.timedelta(days=1)
    
    if period == 'week':
        weekday = queryday.weekday()
        date_start = queryday - datetime.timedelta(days=weekday)
        date_end = date_start + datetime.timedelta(days=7)
    
    if period == 'month':
        date_start = queryday - datetime.timedelta(days=queryday.day-1)
        date_end = date_start + relativedelta(months=1)
    
    return date_start, date_end
    

def get_list(date_start, date_end):
    timezone = datetime.timedelta(hours=3)
    time_start = datetime.datetime.combine(date_start, datetime.datetime.min.time())
    time_end = datetime.datetime.combine(date_end, datetime.datetime.min.time())
    time_min = (time_start - timezone).isoformat() + 'Z'
    time_max = (time_end - timezone).isoformat() + 'Z'
    
    forms_service, drive_service, calendar_service = get_services()
    calendar_id = os.environ.get("CALENDAR")
    events = calendar_service.events().list(calendarId=calendar_id, singleEvents=True, orderBy='startTime', timeMin=time_min, timeMax=time_max).execute()
    return events
    
    
def print_plans(period='week', date=None):
    result = StringIO()
    sys.stdout = result
    
    try:
        date_start, date_end = parse_dates(period, date)
    except:
        print('Проблемы с распознаванием аргументов :(\nОбразец: /list week 20250326')
        return result.getvalue() 

    if period == 'month':
        print(f'Расписание на {months_nom[date_start.month]}:')
    if period == 'week':
        date_end_pretty = date_end - datetime.timedelta(days=1)
        print(f'Расписание с {date_start.day:02d}.{date_start.month:02d} по {date_end_pretty.day:02d}.{date_end_pretty.month:02d}:')
    if period == 'day':
        print(f'Расписание на {date_start.day} {months_gen[date_start.month]}:')
    
    events = get_list(date_start, date_end)
    if not events['items']:
        print('Мероприятий не найдено. Ура! Или не ура?')
        return result.getvalue()
        
    for i, event in enumerate(events['items']):
        print()
        print(f'{i+1}. {event['summary']}')
        try:
            timing = datetime.datetime.fromisoformat(event['start']['dateTime'])
            print(f'Когда: {timing.day:02d}.{timing.month:02d} ({weekdays_short[timing.weekday()]}), {timing.hour:02d}:{timing.minute:02d}')
        except:
            timing_start = datetime.datetime.strptime(event['start']['date'], "%Y-%m-%d").date()
            timing_end = datetime.datetime.strptime(event['end']['date'], "%Y-%m-%d").date() - datetime.timedelta(days=1)
            print(f'Когда: {timing_start.day:02d}.{timing_start.month:02d} ({weekdays_short[timing_start.weekday()]}) - {timing_end.day:02d}.{timing_end.month:02d} ({weekdays_short[timing_end.weekday()]})')
        lines = event['description'].split('\n')
        if lines[0][:4] != 'Где:':
            info = 'Инфо: ' + lines[0]
            lines.pop(0)
            lines.append(info)
        print('\n'.join(lines))

    return result.getvalue()   


def draw_plans(period='week', date=None):
    response = ImageResponse()
    
    Bold192 = ImageFont.truetype("static/HSE_Sans/HSESans-Bold.otf", size=192)
    Bold96 = ImageFont.truetype("static/HSE_Sans/HSESans-Bold.otf", size=96)
    Bold80 = ImageFont.truetype("static/HSE_Sans/HSESans-Bold.otf", size=80)
    SemiBold128 = ImageFont.truetype("static/HSE_Sans/HSESans-SemiBold.otf", size=128)
    SemiBold64 = ImageFont.truetype("static/HSE_Sans/HSESans-SemiBold.otf", size=64)
    SemiBold48 = ImageFont.truetype("static/HSE_Sans/HSESans-SemiBold.otf", size=48)
    Regular192 = ImageFont.truetype("static/HSE_Sans/HSESans-Regular.otf", size=192)
    Regular96 = ImageFont.truetype("static/HSE_Sans/HSESans-Regular.otf", size=96)
    Regular80 = ImageFont.truetype("static/HSE_Sans/HSESans-Regular.otf", size=80)
    Regular64 = ImageFont.truetype("static/HSE_Sans/HSESans-Regular.otf", size=64)
    Regular48 = ImageFont.truetype("static/HSE_Sans/HSESans-Regular.otf", size=48)
    
    try:
        date_start, date_end = parse_dates(period, date)
    except:
        img = Image.open('static/bg_special.png')
        draw = ImageDraw.Draw(img)
        draw.multiline_text(
            (140,228),
            'Проблемы с распознаванием аргументов :(\n\nОбразец:\n/posters week 20250326',
            '#102D69',
            SemiBold128,
            spacing=50
        )
        response.add(img)
        return response
        
    events = get_list(date_start, date_end)
    if not events['items']:
        img = Image.open('static/bg_special.png')
        draw = ImageDraw.Draw(img)
        draw.multiline_text(
            (286,402),
            'Мероприятий не найдено.\nУра! Или не ура?',
            '#102D69',
            SemiBold128,
            spacing=50
        )
        response.add(img)
        return response
      
    service, flags = sample_tools.init(
        sys.argv,
        "calendar",
        "v3",
        __doc__,
        __file__,
        scope="https://www.googleapis.com/auth/calendar.readonly",
    )
    colors = service.colors().get().execute()
    colormap = {}
    for color_id, color in colors['event'].items():
        colormap[color_id] = color['background']
    
    synch = []  
    club = []    
    for event in events['items']:
        if event['colorId'] in colors_synch:
            synch.append(event)
        if event['colorId'] in colors_club:
            club.append(event)
    
    if period == 'month':
        response.set_caption(f'Афиши на {months_nom[date_start.month]}:')
        if len(synch):
            img = Image.open('static/bg_synch.png')
            draw = ImageDraw.Draw(img)
            x = 60
            draw.text((x, 20), months_nom[date_start.month], '#0F2D69', Bold96)
            x_offset = draw.textlength(months_nom[date_start.month], Bold96)
            draw.text((x + x_offset, 20), ' | синхроны', '#8796B4', Regular96)
            y_offset = 0
            for event in synch:
                draw.rectangle([x, 208 + y_offset, x + 30, 238 + y_offset], colormap[event['colorId']])
                timing = datetime.datetime.fromisoformat(event['start']['dateTime'])
                longday = str(timing.day) + ', ' + weekdays_short[timing.weekday()]
                draw.text((x + 65, 190 + y_offset), longday, '#102D69', SemiBold48)    
                draw.text((x + 250, 190 + y_offset), event['summary'], '#102D69', Regular48)
                y_offset += 75
            response.add(img)
            
        if len(club):
            img = Image.open('static/bg_club.png')
            draw = ImageDraw.Draw(img)
            x = 60
            draw.text((x, 20), months_nom[date_start.month], '#0F2D69', Bold96)
            x_offset = draw.textlength(months_nom[date_start.month], Bold96)
            draw.text((x + x_offset, 20), ' | клуб', '#8796B4', Regular96)
            y_offset = 0
            for event in club:
                draw.rectangle([x, 208 + y_offset, x + 30, 238 + y_offset], colormap[event['colorId']])
                timing = datetime.datetime.fromisoformat(event['start']['dateTime'])
                longday = str(timing.day) + ', ' + weekdays_short[timing.weekday()]
                draw.text((x + 65, 190 + y_offset), longday, '#102D69', SemiBold48)    
                draw.text((x + 250, 190 + y_offset), event['summary'], '#102D69', Regular48)
                y_offset += 75
            response.add(img)
            
    if period == 'week' or period == 'day':
        if period == 'week':
            date_end_pretty = date_end - datetime.timedelta(days=1)
            response.set_caption(f'Афиши с {date_start.day:02d}.{date_start.month:02d} по {date_end_pretty.day:02d}.{date_end_pretty.month:02d}:')
        if period == 'day':
            response.set_caption(f'Афиши на {date_start.day} {months_gen[date_start.month]}:')
        date_start, date_end = parse_dates('week', date)
        
        if len(synch):
            for event in synch:
                img = Image.open('static/bg_synch.png')
                draw = ImageDraw.Draw(img)
                x = 96
                
                if date_start.month == date_end.month:
                    header = f'{date_start.day}-{date_end.day} {months_gen[date_start.month]}'
                else:
                    header = f'{date_start.day:02d}.{date_start.month:02d} - {date_end.day:02d}.{date_end.month:02d}'
                draw.text((x, 96), header, '#0F2D69', Bold80)
                x_offset = draw.textlength(header, Bold80)
                draw.text((x + x_offset, 96), ' | синхроны', '#8796B4', Regular80)
                draw.rectangle([x, 282, x+30, 312], colormap[event['colorId']])
                timing = datetime.datetime.fromisoformat(event['start']['dateTime'])
                timetext = f'{timing.day} {months_gen[timing.month]}, {weekdays_long[timing.weekday()]}, {timing.hour:02d}.{timing.minute:02d}'
                draw.text((x + 80, 252), timetext, '#102D69', SemiBold64)
                draw.text((x, 339), event['summary'], '#102D69', Regular64)
                
                lines = event['description'].split('\n')
                for line in lines:
                    if line.find('Сложность') != -1:
                        diff = float(line[10:].replace(' ', ''))
                    if line.find('Где') != -1:
                        if line.find('TBA') == -1 and line.find('ТВА') == -1:
                            place = line[5:]
                        else:
                            place = None
                    if line.find('Взнос') != -1:
                        fee_lines = line[7:].split(',')
                        fees = {'все команды': None, 'взрослые команды': None, 'студенты': None, 'школьники': None}
                        for fl in fee_lines:
                            if fl.find('всех') != -1:
                                fees['все команды'] = fl.split()[0]
                            if fl.find('взрос') != -1:
                                fees['взрослые команды'] = fl.split()[0]
                            if fl.find('студен') != -1:
                                fees['студенты'] = fl.split()[0]
                            if fl.find('школьн') != -1:
                                fees['школьники'] = fl.split()[0]
                        for key, value in fees.items():
                            if value == '0':
                                fees[key] = 'бесплатно'
                draw.text((x, 426), 'сложность: ', '#102D69', Regular48)
                x_offset = draw.textlength('сложность: ', Regular48)
                draw.text((x + x_offset, 426), str(diff), '#7081A5', Regular48)
                y_offset = 0
                if place:
                    y_offset = 65
                    draw.text((x, 491), 'место: ', '#102D69', Regular48)
                    x_offset = draw.textlength('место: ', Regular48)
                    draw.text((x + x_offset, 491), place, '#7081A5', Regular48)
                draw.text((x, 491 + y_offset), 'взнос: ', '#102D69', Regular48)
                x_offset = draw.textlength('взнос: ', Regular48)
                if fees['все команды']:
                    draw.text((x + x_offset, 491 + y_offset), 'все команды' + ' - ' + fees['все команды'], '#7081A5', Regular48)
                else:
                    for key, value in fees.items():
                        if value:
                            draw.text((x + x_offset, 491 + y_offset), key + ' - ' + value, '#7081A5', Regular48)
                            y_offset += 65
                response.add(img)
           
        if len(club):
            for event in club:
                if event['summary'].find('Лига вузов') != -1:
                    img = Image.open('static/bg_special.png')
                    draw = ImageDraw.Draw(img)
                    x = 184
                    draw.text((x, 142), 'Лига вузов', '#0F2D69', Bold192)
                    x_offset = draw.textlength('Лига вузов', Bold192)
                    draw.text((x + x_offset, 142), event['summary'].split('.')[1], '#6F81A5', Regular192)
                    timing = datetime.datetime.fromisoformat(event['start']['dateTime'])
                    timetext = f'{timing.day} {months_gen[timing.month]}, {weekdays_long[timing.weekday()]}, {timing.hour:02d}.{timing.minute:02d}'
                    draw.text((x, 470), timetext, '#102D69', SemiBold128)
                    lines = event['description'].split('\n')
                    for line in lines:
                        if line.find('Сложность') != -1:
                            diff = float(line[10:].replace(' ', ''))
                        if line.find('Где') != -1:
                            if line.find('TBA') == -1 and line.find('ТВА') == -1:
                                place = line[5:]
                            else:
                                place = None
                    draw.text((x, 644), 'сложность: ', '#102D69', Regular96)
                    x_offset = draw.textlength('сложность: ', Regular96)
                    draw.text((x + x_offset, 644), str(diff), '#7081A5', Regular96)
                    y_offset = 0
                    if place:
                        y_offset = 130
                        draw.text((x, 774), 'место: ', '#102D69', Regular96)
                        x_offset = draw.textlength('место: ', Regular96)
                        draw.text((x + x_offset, 774), place, '#7081A5', Regular96)
                    draw.text((x, 774 + y_offset), 'взнос: ', '#102D69', Regular96)
                    x_offset = draw.textlength('взнос: ', Regular96)
                    draw.text((x + x_offset, 774 + y_offset), 'студенческие сборные команды - 300', '#7081A5', Regular96)
                    y_offset += 130
                    draw.text((x + x_offset, 774 + y_offset), 'студенты одного вуза и школьники - ', '#7081A5', Regular96)
                    y_offset += 130
                    x_offset += 880
                    draw.text((x + x_offset, 774 + y_offset), 'бесплатно', '#7081A5', Regular96)
                    response.add(img)
                    
                elif event['summary'].find('Своя игра') != -1:
                    img = Image.open('static/bg_special.png')
                    draw = ImageDraw.Draw(img)
                    x = 184
                    draw.text((x, 142), 'Своя игра', '#0F2D69', Bold192)
                    x_offset = draw.textlength('Своя игра', Bold192)
                    draw.text((x + x_offset, 142), event['summary'].split('.')[1], '#6F81A5', Regular192)
                    timing = datetime.datetime.fromisoformat(event['start']['dateTime'])
                    timetext = f'{timing.day} {months_gen[timing.month]}, {weekdays_long[timing.weekday()]}, {timing.hour:02d}.{timing.minute:02d}'
                    draw.text((x, 470), timetext, '#102D69', SemiBold128)
                    lines = event['description'].split('\n')
                    for line in lines:
                        if line.find('Где') != -1:
                            if line.find('TBA') == -1 and line.find('ТВА') == -1:
                                place = line[5:]
                            else:
                                place = None
                    y_offset = 0
                    if place:
                        y_offset = 130
                        draw.text((x, 644), 'место: ', '#102D69', Regular96)
                        x_offset = draw.textlength('место: ', Regular96)
                        draw.text((x + x_offset, 644), place, '#7081A5', Regular96)
                    draw.text((x, 644 + y_offset), 'взнос: ', '#102D69', Regular96)
                    x_offset = draw.textlength('взнос: ', Regular96)
                    draw.text((x + x_offset, 644 + y_offset), 'студенты и школьники - бесплатно', '#7081A5', Regular96)
                    y_offset += 130
                    draw.text((x + x_offset, 644 + y_offset), 'взрослые - 150', '#7081A5', Regular96)
                    response.add(img)
                    
                else:
                    img = Image.open('static/bg_club.png')
                    draw = ImageDraw.Draw(img)
                    x = 96
                    if date_start.month == date_end.month:
                        header = f'{date_start.day}-{date_end.day} {months_gen[date_start.month]}'
                    else:
                        header = f'{date_start.day:02d}.{date_start.month:02d} - {date_end.day:02d}.{date_end.month:02d}'
                    draw.text((x, 96), header, '#0F2D69', Bold80)
                    x_offset = draw.textlength(header, Bold80)
                    draw.text((x + x_offset, 96), ' | клуб', '#8796B4', Regular80)
                    draw.rectangle([x, 282, x+30, 312], colormap[event['colorId']])
                    timing = datetime.datetime.fromisoformat(event['start']['dateTime'])
                    timetext = f'{timing.day} {months_gen[timing.month]}, {weekdays_long[timing.weekday()]}, {timing.hour:02d}.{timing.minute:02d}'
                    draw.text((x + 80, 252), timetext, '#102D69', SemiBold64)
                    draw.text((x, 339),event['summary'],'#102D69', Regular64)
                    lines = event['description'].split('\n')
                    diff = None
                    fees = None
                    for line in lines:
                        if line.find('Сложность') != -1:
                            diff = float(line[10:].replace(' ', ''))
                        if line.find('Где') != -1:
                            if line.find('TBA') == -1 and line.find('ТВА') == -1:
                                place = line[5:]
                            else:
                                place = None
                        if line.find('Взнос') != -1:
                            fee_lines = line[7:].split(',')
                            fees = {'все команды': None, 'взрослые команды': None, 'студенты': None, 'школьники': None}
                            for fl in fee_lines:
                                if fl.find('всех') != -1:
                                    fees['все команды'] = fl.split()[0]
                                if fl.find('взрос') != -1:
                                    fees['взрослые команды'] = fl.split()[0]
                                if fl.find('студен') != -1:
                                    fees['студенты'] = fl.split()[0]
                                if fl.find('школьн') != -1:
                                    fees['школьники'] = fl.split()[0]
                            for key, value in fees.items():
                                if value == '0':
                                    fees[key] = 'бесплатно'
                            if event['summary'].find('Школьная лига') != -1:
                                fees['школьники'] = '600 за 6 туров'
                    y_offset = 0
                    if diff:
                        draw.text((x, 426 + y_offset), 'сложность: ', '#102D69', Regular48)
                        x_offset = draw.textlength('сложность: ', Regular48)
                        draw.text((x + x_offset, 426 + y_offset), str(diff), '#7081A5', Regular48)
                        y_offset += 65
                    if place:
                        draw.text( (x, 426 + y_offset), 'место: ', '#102D69', Regular48)
                        x_offset = draw.textlength('место: ', Regular48)
                        draw.text((x + x_offset, 426 + y_offset), place, '#7081A5', Regular48)
                        y_offset += 65
                    if fees:
                        draw.text((x, 426 + y_offset), 'взнос: ', '#102D69', Regular48)
                        x_offset = draw.textlength('взнос: ', Regular48)
                        if fees['все команды']:
                            draw.text((x + x_offset, 426 + y_offset), 'все команды' + ' - ' + fees['все команды'], '#7081A5', Regular48)
                        else:
                            for key, value in fees.items():
                                if value:
                                    draw.text((x + x_offset, 426 + y_offset), key + ' - ' + value, '#7081A5', Regular48)
                                    y_offset += 65
                    response.add(img)
    return response
    
    
def poll_plans(period='week', date=None):
    question = 'default question'
    options = []
    try:
        date_start, date_end = parse_dates(period, date)
    except:
        question = 'Проблемы с распознаванием аргументов :('
        options.append(telebot.types.InputPollOption('Образец:'))
        options.append(telebot.types.InputPollOption('/poll week 20250326'))
        return question, options, True

    events = get_list(date_start, date_end)
    if not events['items']:
        question = 'Мероприятий не найдено.'
        options.append(telebot.types.InputPollOption('Ура!'))
        options.append(telebot.types.InputPollOption('Не ура :('))
        return question, options, True
    
    question = 'Готов сыграть:'    
    exclude = ['7', '8']
    for i, event in enumerate(events['items']):
        if len(options) == 9:
            question = '(поместились не все мероприятия, попробуйте выбрать период поменьше)\n' + question
            break
        if event['colorId'] not in exclude:
            timing = datetime.datetime.fromisoformat(event['start']['dateTime'])
            option = f'{event['summary']} ({weekdays_long[timing.weekday()]})'
            options.append(telebot.types.InputPollOption(option))
    options.append(telebot.types.InputPollOption('да, нет, другое'))
       
    return question, options, False
    
    
def form_plans(period='week', date=None):
    result = StringIO()
    sys.stdout = result
    
    result_forms = []
    try:
        date_start, date_end = parse_dates(period, date)
    except:
        print('Проблемы с распознаванием аргументов :(\nОбразец: /forms week 20250326')
        return result.getvalue(), result_forms

    if period == 'month':
        print(f'Формы на {months_nom[date_start.month]}:')
    if period == 'week':
        date_end_pretty = date_end - datetime.timedelta(days=1)
        print(f'Формы с {date_start.day:02d}.{date_start.month:02d} по {date_end_pretty.day:02d}.{date_end_pretty.month:02d}:')
    if period == 'day':
        print(f'Формы на {date_start.day} {months_gen[date_start.month]}:')

    events = get_list(date_start, date_end)
    if not events['items']:
        print('Мероприятий не найдено. Ура! Или не ура?')
        return result.getvalue(), result_forms
    
    for event in events['items']:
        if event['summary'].find('Лига вузов') != -1 \
        or event['summary'].find('Своя игра') != -1 \
        or event['colorId'] == '8':
            continue
        
        newform = {
            'info': {
                'title': event['summary'],
                'documentTitle': f'{event['summary']} ({datetime.datetime.now().strftime('%Y%m%d %H:%M:%S')})'
            },
        }        
        body_update = {'requests': [
            {
            'createItem': {
                'item': {
                    'title': 'Легионер',
                    'description': 'Заполните, пожалуйста, информацию о себе, чтобы мы подобрали для вас лучшую команду.',
                    'pageBreakItem': {}
                },
                'location': {'index': 0},
            }},{
            'createItem': {
                'item': {
                    'title': 'ФИО',
                    'questionItem': {'question': {
                        'required': True,
                        'textQuestion': {}
                    }},
                },
                'location': {'index': 1},
            }},{
            'createItem': {
                'item': {
                    'title': 'ВК или ТГ для связи',
                    'questionItem': {'question': {
                        'required': True,
                        'textQuestion': {}
                    }},
                },
                'location': {'index': 2},
            }},{
            'createItem': {
                'item': {
                    'title': 'Дата рождения',
                    'questionItem': {'question': {
                        'required': True,
                        'dateQuestion': {
                            'includeYear': True
                        }
                    }},
                },
                'location': {'index': 3},
            }},{
            'createItem': {
                'item': {
                    'title': 'Занятость',
                    'questionItem': {'question': {
                        'required': True,
                        'choiceQuestion': {
                            'type': 'RADIO',
                            'options': [{
                                'value': 'Обучаюсь в школе',
                                'goToAction': 'SUBMIT_FORM'
                                },{
                                'value': 'Обучаюсь в НИУ ВШЭ',
                                'goToAction': 'SUBMIT_FORM'
                                },{
                                'value': 'Обучаюсь в другом вузе',
                                'goToAction': 'SUBMIT_FORM'
                                },{
                                'value': 'Другое',
                                'goToAction': 'SUBMIT_FORM'
                                }
                            ]
                        }
                    }},
                },
                'location': {'index': 4},
            }},{
            'createItem': {
                'item': {
                    'title': 'Любые вопросы и сообщения для оргкомитета',
                    'questionItem': {'question': {
                        'textQuestion': {}
                    }},
                },
                'location': {'index': 5},
            }},{
            'createItem': {
                'item': {
                    'title': 'Команда',
                    'description': 'Заполните, пожалуйста, информацию о вашей команде, чтобы мы подготовили всё должным образом.',
                    'pageBreakItem': {}
                },
                'location': {'index': 6},
            }},{
            'createItem': {
                'item': {
                    'title': 'Название команды',
                    'questionItem': {'question': {
                        'required': True,
                        'textQuestion': {}
                    }},
                },
                'location': {'index': 7},
            }},{
            'createItem': {
                'item': {
                    'title': 'ID команды на сайте рейтинга (если нет или не знаете, о чём речь, поставьте 0)',
                    'questionItem': {'question': {
                        'required': True,
                        'textQuestion': {}
                    }},
                },
                'location': {'index': 8},
            }},{
            'createItem': {
                'item': {
                    'title': 'ФИО капитана',
                    'questionItem': {'question': {
                        'required': True,
                        'textQuestion': {}
                    }},
                },
                'location': {'index': 9},
            }},{
            'createItem': {
                'item': {
                    'title': 'ВК или ТГ капитана для связи',
                    'questionItem': {'question': {
                        'required': True,
                        'textQuestion': {}
                    }},
                },
                'location': {'index': 10},
            }},{
            'createItem': {
                'item': {
                    'title': 'Сколько игроков планируется?',
                    'questionItem': {'question': {
                        'required': True,
                        'scaleQuestion': {
                            'low': 1,
                            'high': 6
                        }
                    }},
                },
                'location': {'index': 11},
            }},{
            'createItem': {
                'item': {
                    'title': 'Сколько легионеров (свободных игроков) вы ищете или готовы принять?',
                    'questionItem': {'question': {
                        'required': True,
                        'scaleQuestion': {
                            'high': 5
                        }
                    }},
                },
                'location': {'index': 12},
            }},{
            'createItem': {
                'item': {
                    'title': 'ФИО всех игроков без пропуска в ВШЭ',
                    'questionItem': {'question': {
                        'textQuestion': {
                            'paragraph': True
                        }
                    }},
                },
                'location': {'index': 13},
            }},{
            'createItem': {
                'item': {
                    'title': 'Любые вопросы и сообщения для оргкомитета',
                    'questionItem': {'question': {
                        'textQuestion': {}
                    }},
                },
                'location': {'index': 14},
            }}
        ]}
        
        forms_service, drive_service, calendar_service = get_services()
        form = forms_service.forms().create(body=newform).execute()
        ids = forms_service.forms().batchUpdate(formId=form['formId'], body=body_update).execute()['replies']
        team_section = ids[6]['createItem']['itemId']
        player_section = ids[0]['createItem']['itemId']
        
        timing = datetime.datetime.fromisoformat(event['start']['dateTime'])
        timing_offset = timing - datetime.timedelta(minutes=15)
        if timing.weekday():
            timing_deadline = timing - datetime.timedelta(days=2)
        else:
            timing_deadline = timing - datetime.timedelta(days=3)
        lines = event['description'].split('\n')
        place = 'ул. Костина, 2б'
        diff = None
        fees = None
        for line in lines:
            if line.find('Сложность') != -1:
                diff = float(line[10:].replace(' ', ''))
            if line.find('Где') != -1:
                if line.find('TBA') == -1 and line.find('ТВА') == -1:
                    place = line[5:]
            if line.find('Взнос') != -1:
                fee_lines = line[7:].split(',')
                fees = {
                    'Школьная команда': None, 
                    'Студенческая (все игроки родились не раньше 01.09.2001) команда': None, 
                    'Любая другая команда': None, 
                    'Любая команда': None
                }
                for fl in fee_lines:
                    if fl.find('всех') != -1:
                        fees[list(fees.keys())[3]] = fl.split()[0]
                    if fl.find('взрос') != -1:
                        fees[list(fees.keys())[2]] = fl.split()[0]
                    if fl.find('студен') != -1:
                        fees[list(fees.keys())[1]] = fl.split()[0]
                    if fl.find('школьн') != -1:
                        fees[list(fees.keys())[0]] = fl.split()[0]
                empty = []
                fees_as_request = []
                for key, value in fees.items():
                    if value is None:
                        empty.append(key)
                        continue
                    if value == '0':
                        fees[key] = 'бесплатно'
                    if fees[key] != 'бесплатно':
                        fees[key] += 'р'
                    if event['summary'].find('Школьная лига') != -1:
                        fees[list(fees.keys())[0]] = '600 за 6 туров'
                for key in empty:
                    fees.pop(key)
                for key, value in fees.items():
                    fees_as_request.append({'value': f'{key} - {value}'})
                
        description = ''
        description += f'Дата проведения: {timing.day} {months_gen[timing.month]}, {weekdays_long[timing.weekday()]}\n'
        description += f'Время начала: {timing_offset.hour:02d}:{timing_offset.minute:02d} - сбор, {timing.hour:02d}:{timing.minute:02d} - первый вопрос\n'
        description += f'Место проведения: {place}\n'
        if diff:
            description += f'Сложность: {diff}\n'
        description += '\nОрганизатор: Клуб Интеллектуальных Игр ВШЭ-НН (https://vk.com/chgk_hsenn)\n\n'
        description += f'Обратите внимание! На оформление пропусков в вуз необходимо время, поэтому мы сможем допустить только тех игроков не из ВШЭ, которые зарегистрируются не позже 10 утра {timing_deadline.day} {months_gen[timing_deadline.month]}. Спасибо за понимание!'
        
        header_update = {'requests': [
            {
            'updateFormInfo': {
                'info': {'description': (description)},
                'updateMask': 'description',
            }},{
            'createItem': {
                'item': {
                    'title': 'Кто вы?',
                    'questionItem': {'question': {
                        'required': True,
                        'choiceQuestion': {
                            'type': 'RADIO',
                            'options': [{
                                'value': 'Команда',
                                'goToSectionId': team_section
                                },{
                                'value': 'Игрок в поисках команды',
                                'goToSectionId': player_section
                                }
                            ]
                        }
                    }},
                },
                'location': {'index': 0},
            }}
        ]}
        
        forms_service.forms().batchUpdate(formId=form['formId'], body=header_update).execute()

        if fees:
            fees_update = {'requests': [
                {
                'createItem': {
                    'item': {
                        'title': 'Зачёт, в который входит ваша команда',
                        'questionItem': {'question': {
                            'required': True,
                            'choiceQuestion': {
                                'type': 'RADIO',
                                'options': fees_as_request
                            }
                        }},
                    },
                    'location': {'index': 10}
                }}
            ]}
            forms_service.forms().batchUpdate(formId=form['formId'], body=fees_update).execute()
        
        formfile = drive_service.files().get(fileId=form['formId'], fields='parents').execute()
        previous_parents = ','.join(formfile.get('parents'))
        drive_service.files().update(
            fileId=form['formId'],
            addParents=os.environ.get("FOLDER"),
            removeParents=previous_parents,
            fields='id, parents',
        ).execute()
        
        print()
        print(event['summary'] + ': ' + form['responderUri'] + '\n')
        result_forms.append({'event': event['id'], 'form': form['formId']})
    if not len(result_forms):
        print('(не нужны ни на одно мероприятие)')
    return result.getvalue(), result_forms 
   
   
def update_forms(form_ids):
    forms_service, drive_service, calendar_service = get_services()
    calendar_id = os.environ.get("CALENDAR")
    
    for i in form_ids:
        event = calendar_service.events().get(calendarId=calendar_id, eventId=i['event']).execute()
        form = forms_service.forms().get(formId=i['form']).execute()
        timing = datetime.datetime.fromisoformat(event['start']['dateTime'])
        timing_offset = timing - datetime.timedelta(minutes=15)
        if timing.weekday():
            timing_deadline = timing - datetime.timedelta(days=2)
        else:
            timing_deadline = timing - datetime.timedelta(days=3)
        lines = event['description'].split('\n')
        place = 'ул. Костина, 2б'
        diff = None
        fees = None
        for line in lines:
            if line.find('Сложность') != -1:
                diff = float(line[10:].replace(' ', ''))
            if line.find('Где') != -1:
                if line.find('TBA') == -1 and line.find('ТВА') == -1:
                    place = line[5:]
            if line.find('Взнос') != -1:
                fee_lines = line[7:].split(',')
                fees = {
                    'Школьная команда': None, 
                    'Студенческая (все игроки родились не раньше 01.09.2001) команда': None, 
                    'Любая другая команда': None, 
                    'Любая команда': None
                }
                for fl in fee_lines:
                    if fl.find('всех') != -1:
                        fees[list(fees.keys())[3]] = fl.split()[0]
                    if fl.find('взрос') != -1:
                        fees[list(fees.keys())[2]] = fl.split()[0]
                    if fl.find('студен') != -1:
                        fees[list(fees.keys())[1]] = fl.split()[0]
                    if fl.find('школьн') != -1:
                        fees[list(fees.keys())[0]] = fl.split()[0]
                empty = []
                fees_as_request = []
                for key, value in fees.items():
                    if value is None:
                        empty.append(key)
                        continue
                    if value == '0':
                        fees[key] = 'бесплатно'
                    if fees[key] != 'бесплатно':
                        fees[key] += 'р'
                    if event['summary'].find('Школьная лига') != -1:
                        fees[list(fees.keys())[0]] = '600 за 6 туров'
                for key in empty:
                    fees.pop(key)
                for key, value in fees.items():
                    fees_as_request.append({'value': f'{key} - {value}'})
                
        description = ''
        description += f'Дата проведения: {timing.day} {months_gen[timing.month]}, {weekdays_long[timing.weekday()]}\n'
        description += f'Время начала: {timing_offset.hour:02d}:{timing_offset.minute:02d} - сбор, {timing.hour:02d}:{timing.minute:02d} - первый вопрос\n'
        description += f'Место проведения: {place}\n'
        if diff:
            description += f'Сложность: {diff}\n'
        description += '\nОрганизатор: Клуб Интеллектуальных Игр ВШЭ-НН (https://vk.com/chgk_hsenn)\n\n'
        description += f'Обратите внимание! На оформление пропусков в вуз необходимо время, поэтому мы сможем допустить только тех игроков не из ВШЭ, которые зарегистрируются не позже 10 утра {timing_deadline.day} {months_gen[timing_deadline.month]}. Спасибо за понимание!'
        header_update = {'requests': [
            {
            'updateFormInfo': {
                'info': {
                    'description': (description),
                    'title': event['summary']
                },
                'updateMask': 'description, title',
            }}
        ]}
        forms_service.forms().batchUpdate(formId=form['formId'], body=header_update).execute()
        if fees:
            fees_update = {'requests': [
                {
                'updateItem': {
                    'item': {
                        'title': 'Зачёт, в который входит ваша команда',
                        'questionItem': {'question': {
                            'required': True,
                            'choiceQuestion': {
                                'type': 'RADIO',
                                'options': fees_as_request
                            }
                        }},
                    },
                    'location': {'index': 10},
                    'updateMask': '*'
                }}
            ]}
            forms_service.forms().batchUpdate(formId=form['formId'], body=fees_update).execute()