# from python 3.10 image
FROM python:3.10

WORKDIR /app

# copy the requirements file used for dependencies
COPY requirements.txt .

# install the dependencies
RUN pip install -r requirements.txt

# copy the rest of the files

COPY assistant_conversation_backend /app/assistant_conversation_backend

COPY start.py /app/start.py

# expose the port the application runs on

EXPOSE 8000

# run the application

CMD ["python", "start.py"]