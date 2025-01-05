from io import StringIO
import sys
from stressrnn import StressRNN

def encode(text):
    vowels = ['а', 'ы', 'у', 'э', 'о', 'я', 'и', 'ю', 'е', 'ё']
    code = ''
    for i in range(len(text)-1):
        if text[i] in vowels:
            code += '1' if text[i+1] == '+' else '0'
    if text[-1] in vowels:
        code += '0'
    return code
  
  
def compare(words, list_cur, level=0):
    list_ret = []
    list_fut = []
    for index, example in list_cur:
        word = words[index]
        if len(word) > len(example):
            continue
        flag = True
        for i in range(len(word)):
            if int(word[i]) and not int(example[i]):
                flag = False
        if len(word) == 1:
            flag = True
        if flag:
            if len(word) == len(example) and word[-1] == example[-1]:
                list_ret.append((index-level, level+1))
            if len(word) < len(example) and index < len(words)-1:
                list_fut.append((index+1, example[len(word):]))
    return list_ret + compare(words, list_fut, level+1) if list_fut else list_ret


def generate_start_list(words, example):
    start_list = []
    for i in range(len(words)):
        start_list.append((i, example))
    return start_list


def find_equirhythmics(text, example='очень я тебя люблю'):  
    result = StringIO()
    sys.stdout = result  
    
    stress_rnn = StressRNN()
    
    if not text:
        return result.getvalue()
    text = text.lower().replace('\n', ' ')
    words = text.split()
    code_words = list(map(lambda x: encode(stress_rnn.put_stress(x)), words))
    code_example = encode(stress_rnn.put_stress(example))

    phrases = compare(code_words, generate_start_list(code_words, code_example))
    for index, level in phrases:
        print('> ' + ' '.join(words[index:index+level]))
    
    return result.getvalue()
    
    
def check_equi(text=''):
    text = ' '.join(text.lower().replace('\n', ' ').split())
    result = find_equirhythmics(text)
    return '> ' + text + '\n' == result
    

def find_haiku(text=''):
    result = StringIO(None)
    sys.stdout = result
    
    stress_rnn = StressRNN()
    text = text.lower().replace('\n', ' ')
    words = text.split()
    code_words = list(map(lambda x: encode(stress_rnn.put_stress(x)), words))
    lens = list(map(len, code_words))
    if sum(lens) != 17:
        return result.getvalue()
    start_sum = 0
    first_sep = 0
    for i in range(len(lens)):
        start_sum += lens[i]
        if start_sum > 5:
            return result.getvalue()
        if start_sum == 5:
            first_sep = i + 1
            break
    middle_sum = 0
    second_sep = 0
    for i in range(first_sep, len(lens)):
        middle_sum += lens[i]
        if middle_sum > 7:
            return result.getvalue()
        if middle_sum == 7:
            second_sep = i + 1
            break
    print('🌸')
    print(' '.join(words[:first_sep]))
    print(' '.join(words[first_sep:second_sep]))
    print(' '.join(words[second_sep:]))
    print('🌸')
    return result.getvalue()