### genscene

## Requirements

Make sure you have python 3.12 installed (use pyenv)

## Backend

Set environment variables for OpenAI
> export OPENAI_API_KEY=<the openai api key>
> export OPENAI_MODEL=gpt-4o

Set up python environment
> python -m venv .venv
> source .venv/bin/activate
> pip install -r requirements.txt

Start up Django
> python manage.py migrate
> python manage.py runserver

## Frontend

Start react frontend
- > npm install
- > npm start

