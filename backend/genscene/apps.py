from django.apps import AppConfig
from django.conf import settings
from .actors.home_actor import HomeActor
from .actors.database_actor import DatabaseActor
# from .database_actor import DatabaseActor
from .actor import Actor
from typing import List
import logging
import os
import glob
import importlib

LOGGER = logging.getLogger(__name__)

# all actions with data models should happen through the config class
class GensceneConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "genscene"

    def ready(self):

        openai_config = settings.OPENAI_CONFIG
        self.client = openai_config.client()
        self.deployment = openai_config.deployment()
        LOGGER.info(f"Created the openai client: {self.client} and deployment: {self.deployment}")

        actor_classes = []
        actor_files = glob.glob(os.path.join(os.path.dirname(__file__), "actors", "*_actor.py"))
        for actor_file in actor_files:
            print(f"actor_file: {actor_file}")
            class_file = os.path.splitext(os.path.basename(actor_file))[0]
            class_name = class_file.replace("_", " ").title().replace(" ", "")
            module = importlib.import_module(f".actors.{class_file}", package='genscene')
            cls = getattr(module, class_name)
            actor_classes.append(cls)

        self.actors = {}
        for actor_class in actor_classes:
            actor = actor_class(self.client, self.deployment)
            self.actors[actor.get_name()] = actor
            LOGGER.info(f"Created actor: {actor.get_name()}")

        return super().ready()

    def get_client (self):
        return self.client
    
    def get_deployment (self):
        return self.deployment
    
    def get_actors (self) -> List[Actor]:
        return [self.get_actor(actor_name) for actor_name in self.actors.keys()]

    def get_actor (self, actor_name) -> Actor:
        return self.actors[actor_name].sync()










