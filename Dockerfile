FROM python:3.10-slim-bullseye



WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt



# Copy rest of the application
COPY . .

CMD ["python", "main.py"]