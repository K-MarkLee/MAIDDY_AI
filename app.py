"""
FLASK를 실행
FLASK app을 불러와 호출.
gunicorn 또는 uwsgi를 사용하여 FLASK app을 실행
"""

from app import create_app
from flask_script import Manager
from flask_migrate import MigrateCommand

app = create_app()
manager = Manager(app)

manager.add_command("db", MigrateCommand)

if __name__ == "__main__":
    # 실제 docker에서는 gunicorn이나 flask run으로 실행 가능
    # app.run(host="0.0.0.0", port=5000, debug=True)
    manager.run()