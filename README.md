# Genscene - Generative AI Actors using the OpenAI Assistants API

### Requirements

Make sure you have installed:
- python 3.12 installed (use pyenv)
- node 21.7.2

### Backend

Set environment variables for OpenAI
```
> export OPENAI_API_KEY=<the openai api key>
> export OPENAI_MODEL=gpt-4o
```

Set up python environment
```
> python -m venv .venv
> source .venv/bin/activate
> pip install -r requirements.txt
```

Start up Django
```
> python manage.py migrate
> python manage.py runserver
```

### Frontend

Start react frontend
```
> npm install
> npm start
```


### Database Actor Sample

Set the environment variables. 
```
> export DB_USER=<db username>
> export DB_PASSWORD=<db password>
> export DB_HOST=localhost
> export DB_PORT=3306
> export DB_NAME=genscene_sample
```

Stand up the mysql database if you need one. There is a sample docker 
compose file that will create a database of people. This docker file
will run the 'init_sample_db.sql'. If you use this sample database use
the username and password in the 'init_sample_db.sql'
```
docker compose up
```


