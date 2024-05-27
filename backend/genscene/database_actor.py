import json
import traceback
import sys
import os
import io
from typing import Dict, Any, List
import re
sys.path.append("..")
from genscene.actor import Actor
import json
import logging
from sqlalchemy import create_engine, text, exc

LOGGER = logging.getLogger(__name__)

class DatabaseActor(Actor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        db_user = os.getenv('DB_USER', 'username')
        db_password = os.getenv('DB_PASSWORD', 'password')
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '3306')
        db_name = os.getenv('DB_NAME', 'database_name')
        self.engine = create_engine(f'mysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}')

        # Test the connection
        try:
            with self.engine.connect():
                print("Connection successful")
        except Exception as e:
            print(f"Connection failed: {e}")


    # overriden
    def get_name(self):
        return "database"

    # overriden
    def get_instructions(self):
        return '''You are a database assistant that will answer questions using schema information stored in YAML format. This schema file will be associated with the assistant. You will be asked a question and you will need to retrieve the result set from a sql query run against the database. You will need to follow these steps:
1. Read the question and determine the sql query that needs to be run using the schema information in the assistant file
2. Execute the sql query and retrieve the result set using the function 'execute_sql_query' and passing in the sql query.
3. Display the result set to the user after translating it into a human readable format.

answer as a pirate
'''
    
    # overriden
    # do this lazy to avoid warnings about the database not being available
    def get_description(self):
        return "An example tool to interact with your database using natural language"

    def get_code_resource_files(self) -> Dict[str, io.BytesIO]:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, 'people_schema.yaml')
        LOGGER.info(f"DatabaseActor: reading schema file: {file_path}")
        with open(file_path, 'rb') as file:
            schema = file.read()
        return {'database schema': io.BytesIO(schema)}
    
    # overriden
    def get_tools(self) -> List[Any]:
        return [
            {"type": "code_interpreter"},
            {
                "type": "function",
                "function": {
                    "name": "execute_sql_query",
                    "description": "Retrieve the result set from a sql query run against a database.",
                    "parameters": {
                        "type": "object",
                        "properties": {"sql_query": {"type": "string", "description": "the sql query to execute"}},
                        "required": ["sql_query"],
                    },
                },
            },
        ]

    def execute_sql_query(self, sql_query):
        LOGGER.info(f"DatabaseActor: executing sql query: {sql_query}")
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(sql_query))
                result_dict = [dict(row._mapping) for row in result]
                result_json = json.dumps(result_dict, default=str)
                return result_json
            
        except Exception as e:
            LOGGER.error(f"DatabaseActor: error executing sql query: {sql_query}")
            traceback.print_exc()
            return '{}'




