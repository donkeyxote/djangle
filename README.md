djangle - a django jungle forum

dependencies and higly recommended packages:

- python 3.4
- django v1.8
- pytz
- pillow
- dbms and support libraries for python
- django crispy forms (included in project source)
- kombu
- python-celery

instructions for sending asynchronous mails:

    big fat warning:
        database is used as message queue: switching to other message brokers (e.g. redditmq) is higly recommended for
        production purposes.

    1) move to project directory

        $ cd /path/to/djangle

    2) run a celery worker

        $ celery -A djangle worker -l info

    3) start celery beat service

        $ celery -A djangle beat


    you can also start embed beat inside the worker by enabling workers -B option, this is convenient if you will never
    run more than one worker node.

        $ celery -A djangle worker -B -l info

    celery can be demonized by following the instructions provided in celery documentation (link below):

        http://docs.celeryproject.org/en/latest/tutorials/daemonizing.html
