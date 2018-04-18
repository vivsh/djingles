
import random
from ginger.formatters.base import *


class SimpleFormatter(Formatter):

    def format(self, value, name, source):
        return ">>>>>>> %s" % value


class Item:

    def __init__(self):
        self.a = random.randint(0, 10)
        self.b = random.randint(0, 10)
        self.c = random.randint(0, 10)

source = [Item() for i in range(100)]


class TestPropertySet(FormattedObject):
    a = SimpleFormatter()
    b = Formatter()
    c = Formatter()

    def get_row_attrs(self, row):
        return {"class": "class%s" % row.index}

    def get_cell_attrs(self, cell):
        return {"name": "asdas", "class": "something"}


TestPropertyTable = TestPropertySet.as_table()


if __name__ == '__main__':
    prop = TestPropertyTable(source)
    for p in prop:
        print([a.name for a in p], [a.value for a in p])

