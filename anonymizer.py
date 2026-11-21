import re
import string
from random import SystemRandom
import pymorphy3

rng = SystemRandom()  # Без фиксированного seed.
morph = pymorphy3.MorphAnalyzer()


def digits(value):
    return ''.join(c for c in value if c in string.digits)


def restore_format(template, new_digits):
    """Подставить цифры, оставив все разделители на своих местах."""
    if len(digits(template)) != len(new_digits):
        raise ValueError('Количество цифр не совпадает с исходным форматом')
    iterator = iter(new_digits)
    return ''.join(next(iterator) if c in string.digits else c for c in template)


def checksum(number, weights):
    return str(sum(int(d) * w for d, w in zip(number, weights)) % 11 % 10)


def complete_inn(body):
    """Добавить контрольные разряды к основе из 9 или 10 цифр."""
    if len(body) == 9:
        return body + checksum(body, [2, 4, 10, 3, 5, 9, 4, 6, 8])
    if len(body) == 10:
        number = body + checksum(body, [7, 2, 4, 10, 3, 5, 9, 4, 6, 8])
        return number + checksum(number, [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8])
    raise ValueError('Основа ИНН должна содержать 9 или 10 цифр')


def valid_inn(number):
    if not re.fullmatch(r'[0-9]{10}|[0-9]{12}', number):
        return False
    body = number[:-1] if len(number) == 10 else number[:-2]
    return len(set(number)) > 1 and complete_inn(body) == number


def luhn_sum(number):
    total = 0
    for i, digit in enumerate(reversed(number)):
        value = int(digit)
        if i % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total


def valid_card(number):
    return bool(re.fullmatch(r'[0-9]{13,19}', number)) and luhn_sum(number) % 10 == 0


def numeric_value(value, label):
    pattern = r'\+?[0-9\s()./–—-]+' if label == 'PHONE' else r'[0-9\s-]+'
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise ValueError(f'{label}: недопустимый формат')
    return digits(value)


def anon_inn(value):
    number = numeric_value(value, 'INN')
    if not valid_inn(number):
        raise ValueError('INN: нужны 10 или 12 цифр с верными контрольными разрядами')
    body_length = 9 if len(number) == 10 else 10
    while True:
        body = number[:4] + ''.join(rng.choice(string.digits) for _ in range(body_length - 4))
        new = complete_inn(body)
        if new != number:
            return restore_format(value, new)


def anon_phone(value):
    number = numeric_value(value, 'PHONE')
    if not 10 <= len(number) <= 15:
        raise ValueError('PHONE: ожидается от 10 до 15 цифр')
    while True:
        new = number[:4] + ''.join(rng.choice(string.digits) for _ in number[4:])
        if new != number:
            return restore_format(value, new)


def anon_card(value):
    number = numeric_value(value, 'CARD')
    if not valid_card(number):
        raise ValueError('CARD: нужны 13–19 цифр и корректная проверка Луна')
    # Меняем только середину [6:-4]. Последняя цифра карты остаётся прежней.
    # Одну цифру середины перебираем: ровно одно из 10 значений даёт нужную сумму.
    while True:
        middle = ''.join(rng.choice(string.digits) for _ in range(len(number) - 11))
        for correction in string.digits:
            new = number[:6] + middle + correction + number[-4:]
            if new != number and luhn_sum(new) % 10 == 0:
                return restore_format(value, new)


def anon_email(value):
    if not isinstance(value, str) or value.count('@') != 1:
        raise ValueError('EMAIL: требуется один символ @')
    local, domain = value.split('@')
    domain_labels = domain.split('.')
    if (not re.fullmatch(r'[A-Za-z0-9._%+\-]{1,64}', local)
            or local.startswith('.') or local.endswith('.') or '..' in local
            or not any(c.isalnum() for c in local)
            or len(domain_labels) < 2
            or any(not re.fullmatch(r'[^\W_](?:[^\W_]|-){0,61}[^\W_]|[^\W_]', x)
                   for x in domain_labels)):
        raise ValueError('EMAIL: ожидается обычный адрес вида user@example.com')
    result = []
    for c in local:
        alphabet = (string.ascii_lowercase if c.islower() else
                    string.ascii_uppercase if c.isupper() else
                    string.digits if c.isdigit() else '')
        result.append(rng.choice(alphabet.replace(c, '')) if alphabet else c)
    return ''.join(result) + '@' + domain


NAMES = {
    'masc': ['Иван', 'Пётр', 'Андрей', 'Дмитрий', 'Сергей', 'Алексей', 'Николай', 'Михаил'],
    'femn': ['Анна', 'Мария', 'Ольга', 'Елена', 'Наталья', 'Ирина', 'Татьяна', 'Светлана'],
    'ms-f': ['Саша', 'Женя', 'Валя'],
}
SURNAMES = ['Иванов', 'Петров', 'Сидоров', 'Смирнов', 'Соколов', 'Волков',
            'Орлов', 'Козлов', 'Морозов', 'Новиков', 'Фёдоров', 'Попов']


def apply_case(template, word):
    if template.isupper():
        return word.upper()
    if template.islower():
        return word.lower()
    if template.istitle():
        return word.title()
    raise ValueError('Имя/фамилия: смешанный регистр не поддерживается')


def parse_person(word, kind, case_hint=None):
    variants = [p for p in morph.parse(word) if kind in p.tag
                and p.is_known and 'Abbr' not in p.tag]
    if case_hint:
        suitable = [p for p in variants if p.tag.case == case_hint]
        if suitable:
            variants = suitable
    if not variants:
        raise ValueError('Имя/фамилия не найдены в морфологическом словаре')
    return max(variants, key=lambda p: p.score)


def anon_person(value, kind, case_hint=None):
    if not isinstance(value, str) or not re.fullmatch(r'[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)*', value):
        raise ValueError('Имя/фамилия: ожидается русское слово или части через дефис')
    result = []
    for word in value.split('-'):
        source = parse_person(word, kind, case_hint)
        gender = 'ms-f' if 'ms-f' in source.tag else source.tag.gender
        number, case = source.tag.number, source.tag.case
        required = {x for x in (gender, number, case) if x}
        # Род ms-f у фамилий во множественном числе не задаётся при склонении.
        if kind == 'Surn' and number == 'plur':
            required.discard('ms-f')
        bases = NAMES.get(gender, []) if kind == 'Name' else SURNAMES
        options = set()
        for base in bases:
            for parsed in morph.parse(base):
                if kind not in parsed.tag or parsed.tag.case != 'nomn':
                    continue
                inflected = parsed.inflect(required)
                if inflected is None or not required.issubset(inflected.tag.grammemes):
                    continue
                if (inflected.normal_form.replace('ё', 'е') == source.normal_form.replace('ё', 'е')
                        or inflected.word.replace('ё', 'е') == word.lower().replace('ё', 'е')):
                    continue
                options.add(apply_case(word, inflected.word))
        if not options:
            raise ValueError('Нет замены с нужными родом, числом и падежом')
        result.append(rng.choice(sorted(options)))
    return '-'.join(result)


LABELS = {
    'NAME': 'NAME', 'FIRST_NAME': 'NAME', 'ИМЯ': 'NAME',
    'SURNAME': 'SURNAME', 'LAST_NAME': 'SURNAME', 'ФАМИЛИЯ': 'SURNAME',
    'EMAIL': 'EMAIL', 'E-MAIL': 'EMAIL',
    'INN': 'INN', 'ИНН': 'INN',
    'PHONE': 'PHONE', 'PHONE_NUMBER': 'PHONE', 'НОМЕР ТЕЛЕФОНА': 'PHONE',
    'CARD': 'CARD', 'BANK_CARD': 'CARD', 'CARD_NUMBER': 'CARD', 'НОМЕР БАНКОВСКОЙ КАРТЫ': 'CARD',
}


def anon(text, attributes):
    """Обезличить интервалы [метка, start, end]; end не включается."""
    if not isinstance(text, str):
        raise TypeError('Текст должен быть строкой')
    if not isinstance(attributes, (list, tuple)):
        raise TypeError('Атрибуты должны быть списком')
    if len(attributes) == 3 and isinstance(attributes[0], str):
        attributes = [attributes]  # Также принимается одна тройка из примера методички.
    spans = []
    for item in attributes:
        if not isinstance(item, (list, tuple)) or len(item) != 3:
            raise ValueError('Каждый атрибут должен иметь вид [метка, start, end]')
        label, start, end = item
        if not isinstance(label, str) or label.upper() not in LABELS:
            raise ValueError('Неизвестная метка атрибута')
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
            raise ValueError('Некорректные границы интервала')
        spans.append((start, end, LABELS[label.upper()]))
    spans.sort()
    if any(left[1] > right[0] for left, right in zip(spans, spans[1:])):
        raise ValueError('Интервалы атрибутов не должны пересекаться')

    replacements = []
    for start, end, label in spans:
        value = text[start:end]
        if label in ('NAME', 'SURNAME'):
            # Несколько однозначных предлогов помогают различать омонимичные формы.
            hints = {'к': 'datv', 'ко': 'datv', 'о': 'loct', 'об': 'loct',
                     'обо': 'loct', 'для': 'gent', 'без': 'gent', 'от': 'gent', 'у': 'gent'}
            match = re.search(r'([А-Яа-яЁё-]+)\s+$', text[:start])
            hint = None
            if match:
                previous = match[1]
                hint = hints.get(previous.lower())
                # Предлог может находиться перед соседним именем/фамилией.
                if hint is None and previous.istitle() and any(
                        ('Name' in p.tag or 'Surn' in p.tag) and p.is_known
                        for p in morph.parse(previous)):
                    before = re.search(r'([А-Яа-яЁё]+)\s+$', text[:match.start()])
                    hint = hints.get(before[1].lower()) if before else None
            new = anon_person(value, 'Name' if label == 'NAME' else 'Surn', hint)
        else:
            generator = {'EMAIL': anon_email, 'INN': anon_inn,
                         'PHONE': anon_phone, 'CARD': anon_card}[label]
            new = generator(value)
        replacements.append((start, end, new))

    # Индексы относятся к исходному тексту. Вставка справа налево их не смещает.
    for start, end, new in reversed(replacements):
        text = text[:start] + new + text[end:]
    return text
