from django.apps import AppConfig


class DjinglesConfig(AppConfig):
    name = 'djingles'

    def ready(self):
        self.scan_jinja_tags()

    def scan_jinja_tags(self):
        from djingles import utils
        from djingles.jinja2 import filters, functions
        for module in utils.iter_app_modules("jinja2globals"):
            pass
