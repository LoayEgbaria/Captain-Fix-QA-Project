FROM python:3.12-slim
# Set working directory inside container
WORKDIR /app


COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Let Docker know your app listens on port 8000
EXPOSE 8000
ENTRYPOINT [ "python" , "server.py" ]