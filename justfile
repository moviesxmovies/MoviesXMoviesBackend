# Run development server
[group('server')]
dev port="8000":
    uv run manage.py runserver {{ port }}

# Run development server with external access
[group('server')]
dev0 port="8000":
    #!/usr/bin/env bash
    IP=$(ip -br a | perl -lane 'print $1 if /^enp/ && $F[2] =~ m{([^/]+)}')
    if grep -q $IP main/settings.py; then
        uv run ./manage.py runserver 0.0.0.0:{{ port }}
    else
        echo "Add \"$IP\" to ALLOWED_HOSTS in main/settings.py"
    fi
    uv run manage.py runserver 0.0.0.0:80

alias c:=check
# Check Django project
[group('migrations')]
check:
    uv run manage.py check

alias mm:=makemigrations
# Make model migrations
[group('migrations')]
makemigrations app="":
    uv run manage.py makemigrations {{app}}

alias m:=migrate
# Apply model migrations
[group('migrations')]
migrate app="":
    uv run manage.py migrate {{app}}

# Create a superuser (or update if already exists)
[group('data')]
create-su username="admin" password="admin" email="admin@example.com":
    #!/usr/bin/env bash
    uv run manage.py shell -v0 -c '
    from django.contrib.auth.models import User
    user, _ = User.objects.get_or_create(username="{{ username }}")
    user.email = "{{ email }}"
    user.set_password("{{ password }}") 
    user.is_superuser = True
    user.is_staff = True
    user.save()
    ' 
    echo "✔ Created superuser → {{ username }}:{{ password }}"

# Create a normal user (or update if already exists)
[group('data')]
create-user username password email:
    #!/usr/bin/env bash
    uv run manage.py shell -v0 -c '
    from django.contrib.auth.models import User
    user, _ = User.objects.get_or_create(username="{{ username }}")
    user.email = "{{ email }}"
    user.set_password("{{ password }}") 
    user.is_superuser = False
    user.is_staff = False
    user.save()
    '
    echo "✔ Created user → {{ username }}:{{ password }}"

# Add a new app and install it on settings.py
[group('config')]
startapp app:
    #!/usr/bin/env bash
    uv run manage.py startapp {{ app }}
    APP_CLASS={{ app }}
    APP_CONFIG="{{ app }}.apps.${APP_CLASS^}Config"
    perl -0pi -e "s/(INSTALLED_APPS *= *\[)(.*?)(\])/\1\2    '$APP_CONFIG',\n\3/smg" ./main/settings.py
    echo "✔ App '{{ app }}' created & added to settings.INSTALLED_APPS"

alias sh:=shell
# Open project (django) shell
[group('shell')]
shell:
    uv run manage.py shell

alias dbsh:=dbshell
# Open database shell
[group('shell')]
dbshell:
    uv run manage.py dbshell

# Setup new project
[group('config')]
setup: && migrate create-su set-tz set-media
    #!/usr/bin/env bash
    uv sync
    uv run django-admin startproject main .

# Set Django TimeZone
[group('config')]
set-tz timezone="Atlantic/Canary":
    #!/usr/bin/env bash
    sed -i -E "s@(TIME_ZONE).*@\1 = '{{ timezone }}'@" ./main/settings.py
    if [ $? -eq 0 ]; then
        echo "✔ Fixed TIME_ZONE='{{ timezone }}' and LANGUAGE_CODE='es-es'"
    fi

# Set media settings
[group('config')]
set-media:
    #!/usr/bin/env bash
    echo "" >> ./main/settings.py
    echo "MEDIA_ROOT = BASE_DIR / 'media'" >> ./main/settings.py
    echo "MEDIA_URL = 'media/'" >> ./main/settings.py
    echo "✔ Media settings added to settings.py"

# Remove migrations
[confirm("⚠️ All migrations will be removed. Continue? [yN]:")]
[group('utils')]
rm-migrations:
    #!/usr/bin/env bash
    find . -path "*/migrations/*.py" ! -path "./.venv/*" ! -name "__init__.py" -delete
    find . -path "*/migrations/*.pyc" ! -path "./.venv/*" -delete

# Remove database
[confirm("⚠️ Database will be removed. Continue? [yN]:")]
[group('utils')]
@rm-database:
    rm -f db.sqlite3

# Remove migrations and database. Reset DB artefacts.
[confirm("⚠️ All migrations and database will be removed. Continue? [yN]:")]
[group('utils')]
reset-db: rm-migrations rm-database && makemigrations migrate create-su
    echo "✔ Database reseted."

# Remove virtualenv
[confirm("⚠️ Virtualenv './venv' will be removed. Continue? [yN]:")]
[group('utils')]
rm-venv:
    rm -fr .venv

# Kill existent manage.py processes
[group('utils')]
kill:
    pkill -f "[Pp]ython.*manage.py runserver" || echo "No process"

# Launch tests
[group('utils')]
test pytest_args="":
    uv run pytest -s {{ pytest_args }}

# Generate random secret key
[group('production')]
secret-key:
    #!/usr/bin/env bash
    uv run manage.py shell -v0 -c '
    from django.core.management.utils import get_random_secret_key
    print(get_random_secret_key())
    '

# Make locale folder for all custom apps
[group('i18n')]
makelocale:
    #!/usr/bin/env bash
    uv run manage.py shell -v0 -c '
    from pathlib import Path
    from django.conf import settings

    for folder in settings.BASE_DIR.iterdir():
        if folder.is_dir() and (folder / "apps.py").exists():
            Path(folder / "locale").mkdir(exist_ok=True)
    '
    echo "✔ Each app folder has now a 'locale' folder" 

# Make i18n messages
[group('i18n')]
makemessages locale="es":
    uv run manage.py makemessages -l {{ locale }}

# Compile i18n messages
[group('i18n')]
compilemessages:
    uv run manage.py compilemessages -i .venv

# Open Poedit
[group('i18n')]
poedit app locale="es":
    poedit ./{{ app }}/locale/{{ locale }}/LC_MESSAGES/django.po

# Launch Django RQ worker (development) through watchdog
[group('redis')]
rq:
    uv run watchmedo auto-restart --pattern=tasks.py --recursive -- ./manage.py rqworker 
