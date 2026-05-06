FROM python:3.11-slim
RUN pip install cryptography
WORKDIR /app
COPY script1_root_ca.py .
CMD ["python", "script1_root_ca.py"]