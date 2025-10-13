FROM tiangolo/uwsgi-nginx-flask:python3.12

# Copy application code
COPY ./app /app

# Install dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# The image automatically runs uwsgi-nginx
# It expects your Flask app to be at /app/main.py with a variable named 'app'
