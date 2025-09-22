# Use official Python image as base
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port (commonly 5000 for Flask)
EXPOSE 9000

# Set environment variables for production
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

# Command to run the app (update if your entry point is different)
CMD ["python", "run_dashboard.py"]
