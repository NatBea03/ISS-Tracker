FROM python:3.9


RUN mkdir /app
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip3 install -r /app/requirements.txt
COPY iss_tracker.py /app/iss_tracker.py

COPY iss_tracker.py /code/iss_tracker.py
COPY test_iss_tracker.py /code/test_iss_tracker.py

ENTRYPOINT [ "python" ]
CMD [ "iss_tracker.py" ]


