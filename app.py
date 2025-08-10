from project import create_app, db
from project.models import User, Todo
import click
from flask.cli import with_appcontext

app = create_app()

@click.command('init-db')
@with_appcontext
def init_db_command():
    """데이터베이스 테이블을 생성합니다."""
    db.create_all()
    click.echo('Initialized the database.')

app.cli.add_command(init_db_command)

if __name__ == '__main__':
    app.run(debug=True)