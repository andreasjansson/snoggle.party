FROM    ubuntu:16.04

RUN     apt-get update
RUN     apt-get install -y \
            python-pip

RUN     pip install \
            flask \
            flask-socketio \
            eventlet

ADD     . /opt/snoggle

WORKDIR /opt/snoggle/snoggle

CMD     python server.py
