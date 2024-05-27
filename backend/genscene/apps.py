from django.apps import AppConfig
from django.conf import settings
from .home_actor import HomeActor
from .database_actor import DatabaseActor
# from .database_actor import DatabaseActor
from .actor import Actor
from typing import List
import logging

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

        # should do this dynamically
        self.actors = {}
        # actor_classes = [HomeActor]
        actor_classes = [HomeActor, DatabaseActor]
        for actor_class in actor_classes:
            actor = actor_class(self.client, self.deployment)
            self.actors[actor.get_name()] = actor

        return super().ready()

    def get_client (self):
        return self.client
    
    def get_deployment (self):
        return self.deployment
    
    def get_actors (self) -> List[Actor]:
        return [self.get_actor(actor_name) for actor_name in self.actors.keys()]

    def get_actor (self, actor_name) -> Actor:
        return self.actors[actor_name].sync()










