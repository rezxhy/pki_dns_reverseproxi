FROM python:3.11-slim
RUN pip install cryptography
WORKDIR /app
COPY script2_intermediate_ca.py .
CMD ["python", "script2_intermediate_ca.py"]
