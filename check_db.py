from backend.app import create_app
import os
app = create_app()
print('DB URI:', app.config['SQLALCHEMY_DATABASE_URI'])
print('cwd:', os.getcwd())
