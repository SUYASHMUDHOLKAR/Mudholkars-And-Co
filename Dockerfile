FROM python:3.11-slim

WORKDIR /app

# Install all dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire company
COPY . .

# Default: run all agents
CMD ["python", "run_all_agents.py"]
