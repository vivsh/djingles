
from jinja2.nodes import CallBlock
from jinja2.ext import Extension
from djingles import html

class PreExtension(Extension):
    tags = set(['pre'])

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        body = parser.parse_statements(['name:endpre'], drop_needle=True)
        return CallBlock(
            self.call_method('_format_content'),
            [],
            [],
            body
        ).set_lineno(lineno)

    def _format_content(self, caller):
        block = caller()
        block = self._format_whitespace(block)
        return block

    def _format_whitespace(self, block):
        blocks = []
        current = []
        empty = 0
        for ln in block.strip().splitlines():
            ln = ln.strip()
            if not ln:
                empty += 1
            else:
                empty = 0
            if not ln and current:
                content = "<p>%s</p>" % ("<br>".join(current))
                current = []
                blocks.append(content)
            elif ln:
                current.append(ln)
            elif empty <= 2:
                blocks.append("<br>")
        if current:
            content = "<p>%s</p>" % ("<br>".join(current))
            blocks.append(content)
        return "".join(blocks)


class TableExtension(Extension):
    tags = set(("table",))

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        body = parser.parse_statements(['name:endtable'], drop_needle=True)
        return CallBlock(self.call_method('_process_table'),
                               [], [], body).set_lineno(lineno)

    def _process_table(self, caller):
        block = caller()
        delimiter = "||"
        block = self._format_whitespace(block, delimiter)
        return block

    def _format_row(self, row, delimiter):
        columns = row.split(delimiter)
        return html.tr[[html.td(valign='top')[a] for a in columns]]

    def _format_whitespace(self, block, delimiter):
        blocks = []
        current = []
        empty = 0
        for ln in block.strip().splitlines():
            ln = ln.strip()
            if not ln:
                empty += 1
            else:
                empty = 0
            if not ln and current:
                content = self._format_row("<br>".join(current), delimiter)
                current = []
                blocks.append(content)
            elif ln:
                current.append(ln)
            elif empty <= 2:
                blocks.append("<br>")
        if current:
            content = self._format_row("<br>".join(current), delimiter)
            blocks.append(content)
        root = html.table(style="width:100%")[
            html.tbody[
                blocks
            ]
        ]
        return str(root)