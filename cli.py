import timetable
import datetime
import sys

def offline_dump():
    old_stdout = sys.stdout
    text = ''

    args = '/guests'.split()
    date = datetime.date.today() + datetime.timedelta(days=2)
    date = date.strftime("%Y%m%d")
    text += timetable.get_guests(args[1] if len(args)>1 else 'day', args[2] if len(args)>2 else date)
    text += '\n'
    args = '/plan next week'.split()
    date = datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())
    if 'next' in args:
        date += datetime.timedelta(days=7)
    date = date.strftime("%Y%m%d")
    period = 'week'
    text += timetable.print_plans(period, date)
    text += '\n'
    text += timetable.form_plans(period, date)
    text += '\n'
    question, options, is_closed = timetable.poll_plans(period, date)
    text += question
    for opt in options:
        text += '\n- ' + opt.text
    response = timetable.draw_plans(period, date)
    response.move_to('dump')

    sys.stdout = old_stdout
    with open('dump/info.txt', 'w') as f:
        f.write(text)
    return '> saved main info in \'dump\''
    
