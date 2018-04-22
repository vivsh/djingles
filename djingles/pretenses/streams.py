
from decimal import Decimal
from datetime import datetime, timedelta, date, time
from django.contrib.gis.geos.point import Point
import random
import string

from django.core.files.base import ContentFile
from . import utils


__all__ = [
    "IntegerStream",
    "FloatStream",
    "DateTimeStream",
    "DateStream",
    "TimeStream",
    "DecimalStream",
    "WordStream",
    "FirstNameStream",
    "LastNameStream",
    "FullNameStream",
    "RandomPasswordStream",
    "PasswordStream",
    "ParagraphStream",
    "SentenceStream",
    "IPAddressStream",
    "PointStream",
    "ChoiceStream",
    "ImageStream",
    "FileStream",
    "ForeignKeyStream",
    "OneToOneStream",
    "ManyToManyStream",
    "DefaultValueStream",
    "ValueStream",
    "NameStream",
    "SlugStream"
]


class IntegerStream(object):

    def __init__(self, start=0, end=255):
        self.start = start
        self.end = end

    def next(self, field):
        return random.randint(self.start, self.end)


class FloatStream(IntegerStream):

    def __init__(self, start=0, end=100.0):
        super(FloatStream, self).__init__(start, end)

    def next(self, field):
        return random.uniform(0.000001, 9999999999.99999999)


class SentenceStream(object):

    def next(self, field):
        stream = WordStream()
        result = " ".join(stream.next(field) for _ in range(random.randint(4, 9)))
        return "%s." % result.capitalize()


class ParagraphStream(object):

    def __init__(self, minimum=1, maximum=10, html=False):
        self.minimum = minimum
        self.maximum = maximum
        self.html = html

    def create_paragraph(self, field):
        stream = SentenceStream()
        return " ".join(stream.next(field) for _ in range(random.randint(5, 10)))

    def next(self, field):
        limit = random.randint(self.minimum,self.maximum)
        result = "\n".join(self.create_paragraph(field) for _ in range(limit))
        if field.max_length:
            result = result[:field.max_length]
        if self.html:
            html_result = []
            for item in result.splitlines(True):
                html_result.append('<p>'+item+'</p>')
            return ''.join(html_result)
        return result


class WordStream(object):

    def __init__(self, min_length=4, max_length=16, total=1):
        self.min_length = min_length
        self.max_length = max_length
        self.total = total

    def next(self, field):
        words = []
        for i in range(self.total):
            limit = random.randint(self.min_length, self.max_length)
            word = "".join(random.sample(string.ascii_lowercase, limit))
            words.append(word)
        return " ".join(words)


class FullNameStream(object):

    def next(self, field):
        return " ".join(NameStream().next(field) for _ in range(2))


class SlugStream(WordStream):

    def next(self, field):
        return super(SlugStream, self).next(field).replace(" ", "-")


class NameStream(object):

    def next(self, field):
        return WordStream(min_length=4, max_length=8).next(field)


class FirstNameStream(NameStream):
    pass


class LastNameStream(NameStream):
    pass


class DateTimeStream(object):

    def __init__(self, start=None, end=None, aware=True):
        if start is None:
            start = datetime(1900, 1, 1)
        if end is None:
            end = datetime.now()
        if end < start:
            raise ValueError("End %s can't be less than start %s" % (end, start))
        self.start = start
        self.end = end
        self.aware = aware

    def next(self, field):
        delta = (self.end-self.start).total_seconds()
        interval = random.randint(1, int(delta))
        result = self.start + timedelta(seconds=interval)
        if self.aware:
            from django.utils import timezone
            result = timezone.make_aware(result, timezone.get_default_timezone())
        return result


class DateStream(DateTimeStream):

    def __init__(self, start=None, end=None):
        if start is None:
            start = date(1900, 1, 1)
        if end is None:
            end = datetime.now()
        super(DateStream, self).__init__(datetime.combine(start, time()),
                                            datetime.combine(end, time()), False)

    def next(self, field):
        result = super(DateStream, self).next(field)
        return result.date()


class TimeStream(DateTimeStream):

    def __init__(self, start=None, end=None):
        if start is None:
            start = time(0, 0, 0)
        if end is None:
            end = time(23, 59, 59)
        if start > end:
            raise ValueError
        start, end = map(self.to_datetime, (start, end))
        super(TimeStream, self).__init__(start, end, False)

    @staticmethod
    def to_datetime(stamp):
        return datetime.combine(date.today(), stamp)

    def next(self, field):
        result = super(TimeStream, self).next(field)
        return result.time()


class IPAddressStream(object):

    def next(self, field):
        return ".".join(str(random.randint(1, 254)) for _ in range(4))


class ImageStream(object):
    def __init__(self, paths):
        self.folder = paths

    def next(self, field):
        filename = utils.get_random_image(self.folder)
        return ContentFile(open(filename, 'rb').read())


class FileStream(object):
    
    def __init__(self, paths, extensions=None):
        self.folders = paths
        self.extensions = extensions

    def next(self, field):
        filename = utils.get_random_file(self.folders, self.extensions)
        return ContentFile(open(filename, 'rb').read())


class DecimalStream(object):

    def __init__(self, start=None, end=None):
        if start is None:
            start = 0.0
        if end is None:
            end = 9999999999.999999
        self.start = float(start)
        self.end = float(end)

    def next(self, field):
        value = random.uniform(self.start, self.end)
        value = str(value*10**field.decimal_places)[:field.max_digits]
        return Decimal(value)/10**field.decimal_places


class PasswordStream(object):

    def __init__(self, word):
        from django.contrib.auth.hashers import make_password
        self.word = word
        self.hash_code = make_password(self.word)

    def next(self, field):
        return self.hash_code


class RandomPasswordStream(object):

    def __init__(self, max_length=32, min_length=1, specials=1, capitals=1):
        self.max_length = max_length
        self.min_length = min_length
        self.specials = specials
        self.capitals = capitals
        if max_length < min_length:
            raise ValueError("max length should be greater than min length")

    def next(self, field):
        list_special_char = ['!','@','#','$','%','^','&','*','(',')','+','_','~','<','>','|','{','}','[',']','`']
        password = ""
        size = random.randint(self.min_length, self.max_length)
        stream = WordStream()
        while len(password) < size:
            password += stream.next(field)
        password = password[:size]
        result = list(password)
        positions = set(range(len(password)))

        specials = self.specials % size
        special_positions = random.sample(range(len(password)), specials)
        positions.difference_update(special_positions)

        for i in special_positions:
            result[i] = random.choice(list_special_char)

        capitals = self.capitals % len(positions)
        for i in random.sample(positions, capitals):
            result[i] = result[i].upper()

        return "".join(result)


class ChoiceStream(object):
    def __init__(self, choices):
        self.choices = choices

    def next(self, field):
        return random.choice(self.choices)


class ValueStream(object):
    def __init__(self, value):
        self.value = value

    def next(self, field):
        return self.value


class DefaultValueStream(object):
    def next(self, field):
        return field.default


class PointStream(object):
    def __init__(self, longitude=None, latitude=None, radius=None):
        self.longitude = longitude
        self.latitude = latitude
        self.radius = radius

    def next(self, field):
        from geopy.distance import VincentyDistance
        longitude = random.randint(-179, 179) if self.longitude is None else self.longitude
        latitude = random.randint(-179, 179) if self.latitude is None else self.latitude
        radius = random.randint(100, 6000) if self.radius is None else self.radius
        d = VincentyDistance(kilometers=radius)
        bearing = random.randint(0, 359)
        p = d.destination((latitude, longitude), bearing)
        return Point(x=p.longitude, y=p.latitude)


class ForeignKeyStream(object):
    def __init__(self, queryset):
        self.queryset = queryset
        self.total = len(self.queryset)

    def next(self, field):
        i = random.randint(0, self.total-1)
        return self.queryset[i]


class OneToOneStream(ForeignKeyStream):
    pass


class ManyToManyStream(object):
    def __init__(self, queryset, limit=None):
        self.queryset = queryset
        self.total = len(self.queryset)
        self.limit = limit

    def next(self, field):
        size = self.limit if self.limit is not None else random.randint(0, self.total/2-1)
        i = random.randint(0, self.total-1)
        items = self.queryset[i: i+size]
        return items
