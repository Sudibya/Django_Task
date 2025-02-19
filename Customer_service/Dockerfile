# Use the official Python image
FROM python:3.10

# Install PostgreSQL client tools (Fixes `pg_isready` not found)
RUN apt-get update && apt-get install -y postgresql-client

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 8001 for Django
EXPOSE 8001

# Wait for PostgreSQL, run migrations, and start Django
CMD ["sh", "-c", "until pg_isready -h db_customer -p 5432; do echo 'Waiting for PostgreSQL...'; sleep 2; done; python manage.py migrate && python manage.py runserver 0.0.0.0:8001"]
