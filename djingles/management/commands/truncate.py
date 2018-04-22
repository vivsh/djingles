
import pprint
from optparse import make_option
from django.apps import apps
from django.conf import settings
from djingles import pretenses
from django.core.management import BaseCommand, CommandError


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("models", nargs='*', help="Name of the model that you wish to truncate")

    def handle(self, **options):
        if not settings.DEBUG:
            raise CommandError("This command cannot be run in production environment")
        models = options["models"]
        if not models:
            for app in apps.get_app_configs():
                self.truncate_app(app)
        else:
            for name in models:
                if "." in name:
                    app_label, model_name = name.split(".", 1)
                    model = apps.get_model(app_label, model_name)
                    self.truncate_model(model)
                else:
                    app = apps.get_app_config(name)
                    self.truncate_app(app)

    def truncate_app(self, app):
        models = app.get_models()
        map(self.truncate_model, models)

    def truncate_model(self, model):
        model.objects.all().delete()
