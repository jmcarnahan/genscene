import logging
from django.core.management.base import BaseCommand

from genscene.models import Assistant, File, Thread
from django.conf import settings
from django.db import transaction

LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Purge all data from the database'

    def handle(self, *args, **options):
        help = 'Purge all data from the database and assistants'

        openai_client = settings.OPENAI_CONFIG.client()

        LOGGER.info("Purging assistants")
        for assistant in Assistant.objects.all():
            assistant_id = assistant.assistant_id
            try:
                LOGGER.info(f"Deleting assistant {assistant_id}")
                openai_client.beta.assistants.delete(assistant_id)
            except:
                LOGGER.error(f"Could not delete assistant {assistant_id}")
        Assistant.objects.all().delete()

        LOGGER.info("Purging files")
        for file in File.objects.all():
            file_id = file.file_id
            try:
                LOGGER.info(f"Deleting file {file_id}")
                openai_client.files.delete(file_id)
            except:
                LOGGER.error(f"Could not delete file {file_id}")
        File.objects.all().delete()

        LOGGER.info("Purging threads")
        for thread in Thread.objects.all():
            thread_id = thread.thread_id
            try:
                LOGGER.info(f"Deleting thread {thread_id}")
                openai_client.beta.threads.delete(thread_id)
            except:
                LOGGER.error(f"Could not delete thread {thread_id}")
        Thread.objects.all().delete()

        transaction.commit()
        return