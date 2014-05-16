import os

from django.conf import settings

sqlite_path =  os.path.join(settings.PROJECT_ROOT, 'database/database.sqlite3')
print sqlite_path

