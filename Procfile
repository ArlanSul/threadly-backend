web: gunicorn threadly.wsgi --bind 0.0.0.0:$PORT --log-file -
release: python manage.py migrate && python manage.py collectstatic --noinput