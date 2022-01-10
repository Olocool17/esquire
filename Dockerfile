# syntax=docker/dockerfile:1
FROM python:slim
WORKDIR /Esquire
COPY pip_requirements.txt pip_requirements.txt
RUN pip3 install -r pip_requirements.txt
RUN apt-get update && apt-get install -y ffmpeg libopus0
COPY . .
CMD ["python3", "main.py", "--host=0.0.0.0"]