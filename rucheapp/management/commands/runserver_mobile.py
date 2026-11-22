from django.contrib.staticfiles.management.commands.runserver import Command as RunserverCommand


class Command(RunserverCommand):
    help = "Lance BeeFlow sur le réseau local pour permettre le scan des QR par téléphone."
    default_addr = "0.0.0.0"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.set_defaults(addrport="0.0.0.0:8000")
