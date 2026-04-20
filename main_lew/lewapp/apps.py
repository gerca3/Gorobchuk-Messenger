from django.apps import AppConfig


class LewappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lewapp'

    def ready(self):
        import lewapp.signals
