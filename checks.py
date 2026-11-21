from anonymizer import *

def span(text, label, value):
    start = text.index(value)
    return [label, start, start + len(value)]


def non_digits(value):
    return [(i, c) for i, c in enumerate(value) if c not in string.digits]


# Контрольные примеры не генерируются проверяемыми функциями.
assert valid_inn('770698959438')
assert valid_inn('7707083893')
assert not valid_inn('770698959439')
assert not valid_inn('0000000000')
assert valid_card('4561261212345467')
assert valid_card('4111111111111111')
assert not valid_card('4111111111111112')

# Сохранение формата, частей номера и контрольных разрядов: 200 замен каждого типа.
samples = {
    'EMAIL': ['ivan.petrov+7@Example.COM', 'a@пример.рф'],
    'INN': ['770698959438', '7707 08389-3'],
    'PHONE': ['+7 (999) 123-45-67', '8 495 123 45 67', '+1 (202) 555-0123'],
    'CARD': ['4561 2612 1234 5467', '4111-1111-1111-1111', '4222222222222'],
}
for label, values in samples.items():
    for i in range(200):
        old = values[i % len(values)]
        new = anon(old, [label, 0, len(old)])
        assert new != old
        if label == 'EMAIL':
            assert new.split('@')[1] == old.split('@')[1]
            assert len(new) == len(old)
        else:
            assert len(new) == len(old) and non_digits(new) == non_digits(old)
            a, b = digits(old), digits(new)
            if label == 'INN':
                assert b[:4] == a[:4] and valid_inn(b)
            elif label == 'PHONE':
                assert b[:4] == a[:4]
            else:
                assert b[:6] == a[:6] and b[-4:] == a[-4:] and valid_card(b)

# Длины карт 13–19 цифр; последняя цифра исходника вычисляется отдельно.
for length in range(13, 20):
    body = '456126' + '3' * (length - 7)
    old = next(body + d for d in string.digits if luhn_sum(body + d) % 10 == 0)
    for _ in range(20):
        new = anon_card(old)
        assert len(new) == length and new[:6] == old[:6] and new[-4:] == old[-4:]
        assert new != old and valid_card(new)

# Грамматические свойства задаются явно, а не берутся из результата генератора.
morph_cases = [
    ('Иван', 'NAME', {'masc', 'sing', 'nomn'}),
    ('Ивана', 'NAME', {'masc', 'sing', 'gent'}),
    ('Ивану', 'NAME', {'masc', 'sing', 'datv'}),
    ('Ивана', 'NAME', {'masc', 'sing', 'accs'}),
    ('Иваном', 'NAME', {'masc', 'sing', 'ablt'}),
    ('Иване', 'NAME', {'masc', 'sing', 'loct'}),
    ('Анна', 'NAME', {'femn', 'sing', 'nomn'}),
    ('Анны', 'NAME', {'femn', 'sing', 'gent'}),
    ('Анне', 'NAME', {'femn', 'sing', 'datv'}),
    ('Анну', 'NAME', {'femn', 'sing', 'accs'}),
    ('Анной', 'NAME', {'femn', 'sing', 'ablt'}),
    ('Анне', 'NAME', {'femn', 'sing', 'loct'}),
    ('Саша', 'NAME', {'ms-f', 'sing', 'nomn'}),
    ('Иваны', 'NAME', {'masc', 'plur', 'nomn'}),
    ('Иванов', 'SURNAME', {'masc', 'sing', 'nomn'}),
    ('Иванову', 'SURNAME', {'masc', 'sing', 'datv'}),
    ('Ивановым', 'SURNAME', {'masc', 'sing', 'ablt'}),
    ('Иванова', 'SURNAME', {'femn', 'sing', 'nomn'}),
    ('Ивановой', 'SURNAME', {'femn', 'sing', 'gent'}),
    ('Иванову', 'SURNAME', {'femn', 'sing', 'accs'}),
    ('Ивановы', 'SURNAME', {'plur', 'nomn'}),
    ('Ивановых', 'SURNAME', {'plur', 'gent'}),
    ('Ивановым', 'SURNAME', {'plur', 'datv'}),
    ('Ивановыми', 'SURNAME', {'plur', 'ablt'}),
]
for old, label, required in morph_cases:
    kind = 'Name' if label == 'NAME' else 'Surn'
    # Падеж помогает разобрать неоднозначную форму; в anon подсказка берётся из предлога.
    case = next(x for x in required if x in {'nomn', 'gent', 'datv', 'accs', 'ablt', 'loct'})
    for _ in range(5):
        new = anon_person(old, kind, case)
        assert new != old
        assert any(kind in p.tag and required.issubset(p.tag.grammemes) for p in morph.parse(new)), (old, new, required)

for old in ['иван', 'ИВАН', 'Анна-Мария', 'Сидоров-Петров']:
    label = 'SURNAME' if old == 'Сидоров-Петров' else 'NAME'
    new = anon(old, [label, 0, len(old)])
    assert old != new and old.count('-') == new.count('-')
    assert (old.islower(), old.isupper(), old.istitle()) == (new.islower(), new.isupper(), new.istitle())

for old in ['к Анне', 'об Анне', 'для Анны', 'о Петровой', 'к Ивану Петрову']:
    words = old.split()
    label = 'SURNAME' if words[-1].startswith('Петров') else 'NAME'
    item = span(old, label, words[-1])
    new = anon(old, [item])
    assert new.startswith(old[:item[1]]) and new != old
    case = {'к': 'datv', 'об': 'loct', 'для': 'gent', 'о': 'loct'}[words[0]]
    assert any(p.tag.case == case for p in morph.parse(new.split()[-1]))

# Проверка, что вне интервалов, в том числе между соседними, текст не меняется.
old = 'До: Иван/Петров; email=a@example.com. После!'
items = [span(old, 'NAME', 'Иван'), span(old, 'SURNAME', 'Петров'),
         span(old, 'EMAIL', 'a@example.com')]
new = anon(old, list(reversed(items)))
assert re.fullmatch(r'До: [А-Яа-яЁё]+/[А-Яа-яЁё]+; email=[a-z]@example\.com\. После!', new)
assert anon('', []) == ''
assert anon('Текст без ПДн', []) == 'Текст без ПДн'
assert anon('ИванПетров', [['NAME', 0, 4], ['SURNAME', 4, 10]]) != 'ИванПетров'
print('Проверки структуры, морфологии и контрольных разрядов пройдены.')

def expect_error(title, action):
    try:
        action()
    except (ValueError, TypeError) as error:
        print(f'{title}: {error}')
    else:
        raise AssertionError(f'Ожидалась ошибка: {title}')


bad_inputs = [
    ('Текст не строка', lambda: anon(None, [])),
    ('Вместо списка передан None', lambda: anon('Иван', None)),
    ('Неполная тройка', lambda: anon('Иван', [['NAME', 0]])),
    ('Неизвестная метка', lambda: anon('Иван', ['UNKNOWN', 0, 4])),
    ('Отрицательный индекс', lambda: anon('Иван', ['NAME', -1, 4])),
    ('Выход за границы', lambda: anon('Иван', ['NAME', 0, 20])),
    ('Пустой интервал', lambda: anon('Иван', ['NAME', 0, 0])),
    ('Индекс не целый', lambda: anon('Иван', ['NAME', 0.0, 4])),
    ('Пересекающиеся интервалы', lambda: anon('Иван', [['NAME', 0, 4], ['NAME', 1, 4]])),
    ('Дублирующиеся интервалы', lambda: anon('Иван', [['NAME', 0, 4], ['NAME', 0, 4]])),
    ('Слово не является именем', lambda: anon('стол', ['NAME', 0, 4])),
    ('Инициал', lambda: anon('И.', ['NAME', 0, 2])),
    ('Смешанный регистр', lambda: anon('иВаН', ['NAME', 0, 4])),
    ('Почта без @', lambda: anon_email('user.example.com')),
    ('Почта с двумя @', lambda: anon_email('user@@example.com')),
    ('Пустой логин', lambda: anon_email('@example.com')),
    ('Неправильный домен', lambda: anon_email('user@-example.com')),
    ('Короткий ИНН', lambda: anon_inn('123')),
    ('Неверный контрольный разряд ИНН', lambda: anon_inn('770698959439')),
    ('Буквы вместо ИНН', lambda: anon_inn('7706ABC59438')),
    ('Короткий телефон', lambda: anon_phone('+7 (999)')),
    ('Буквы в телефоне', lambda: anon_phone('телефон неизвестен')),
    ('Частичная карта', lambda: anon_card('**** **** **** 1111')),
    ('Неверная проверка Луна', lambda: anon_card('4111 1111 1111 1112')),
]
for title, action in bad_inputs:
    expect_error(title, action)
print(f'Все {len(bad_inputs)} проверок неожиданных значений пройдены.')
