# Djangle
### a Django jungle forum

## dependencies and highly recommended packages:

* python 3.4
* Django v1.8
* pytz
* pillow
* dbms and support libraries for python
* Django crispy forms (included in project source)
* kombu
* celery

## configuration instruction

* create an SQL database
* configure database and email settings by editing file *config.ini* (fields' names are self-explanatory)

## initialization and run

move to project directory

    $ cd /path/to/djangle
make migrations for forum app

    $ python3 manage.py makemigrations forum

synchronize the database state with the current set of models

    $ python3 manage.py migrate

create a superuser for Django admin

    $ python3 manage.py createsuperuser

let the show begin

    $ python3 manage.py runserver

## instructions for mail and self-removal ban services:

**big fat warning:**
> Django database is used as message queue: moving to other message brokers (e.g. redditmq) is highly recommended for
> production purposes.

move to project directory

    $ cd /path/to/djangle

start a celery worker

    $ celery -A djangle worker -l info

open another terminal tab in project's root directory and start celery beat service
(this is only required for asynchronous tasks like asynchronous subscriptions, and ban evaluation)

    $ celery -A djangle beat

you can also start embed beat inside the worker by enabling workers -B option, this is convenient if you will never
run more than one worker node.

    $ celery -A djangle worker -B -l info

celery can be demonized by following the instructions provided in the [celery documentation]
(http://docs.celeryproject.org/en/latest/tutorials/daemonizing.html)
