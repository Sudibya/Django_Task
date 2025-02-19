# Use the official Python image
FROM python:3.10

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port 8000 for Django
EXPOSE 8000

# Run migrations and start the Django server
CMD ["sh", "-c", "
    until pg_isready -h postgres_db -p 5432; do
        echo 'Waiting for PostgreSQL...';
        sleep 2;
    done;
    python manage.py migrate &&
    python manage.py runserver 0.0.0.0:8000"]
