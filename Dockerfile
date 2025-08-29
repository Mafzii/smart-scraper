FROM python:3.11-slim

# Install system deps for Playwright Chromium
RUN apt-get update && apt-get install -y \
    wget gnupg curl git unzip \
    libnss3 libxss1 libasound2 libatk1.0-0 libatk-bridge2.0-0 \
    libx11-xcb1 libdrm2 libgbm1 libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install --with-deps chromium

COPY . .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
