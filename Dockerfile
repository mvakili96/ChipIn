FROM tiangolo/uwsgi-nginx-flask:python3.12

# Copy application code
COPY ./app /app

# The image automatically runs uwsgi-nginx
# It expects your Flask app to be at /app/main.py with a variable named 'app'
