from django.apps import AppConfig


class AllocationappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'allocationapp'

    def ready(self):
        from . import schedulers
        schedulers.start_deallocate_schedular()
