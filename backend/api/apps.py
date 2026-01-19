# Import Django base class, define app class and name

from django.apps import AppConfig

class ApiConfig(AppConfig):
    # Use 64 bit IDs
    default_auto_field = 'django.db.models.BigAutoField'
    # Define app name
    name = 'api'