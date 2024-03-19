from dotenv import load_dotenv
load_dotenv()

from parliament import Context
from flask import Request, jsonify
import json
from cloudevents.http import from_http
from langflow import load_flow_from_json
import logging as logger
import os
from sqlalchemy import create_engine, Column, String, JSON, MetaData, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Session
import uuid
import time

log_level = os.getenv("LOG_LEVEL", "info").upper()
logger.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=log_level)


# # parse request body, json data or URL query parameters
# def payload_print(req: Request) -> str:
#     if req.method == "POST":
#         if req.is_json:
#             return json.dumps(req.json) + "\n"
#         else:
#             # MultiDict needs some iteration
#             ret = "{"

#             for key in req.form.keys():
#                 ret += '"' + key + '": "'+ req.form[key] + '", '

#             return ret[:-2] + "}\n" if len(ret) > 2 else "{}"

#     elif req.method == "GET":
#         # MultiDict needs some iteration
#         ret = "{"

#         for key in req.args.keys():
#             ret += '"' + key + '": "' + req.args[key] + '", '

#         return ret[:-2] + "}\n" if len(ret) > 2 else "{}"


# # pretty print the request to stdout instantaneously
# def pretty_print(req: Request) -> str:
#     ret = str(req.method) + ' ' + str(req.url) + ' ' + str(req.host) + '\n'
#     for (header, values) in req.headers:
#         ret += "  " + str(header) + ": " + values + '\n'

#     if req.method == "POST":
#         ret += "Request body:\n"
#         ret += "  " + payload_print(req) + '\n'

#     elif req.method == "GET":
#         ret += "URL Query String:\n"
#         ret += "  " + payload_print(req) + '\n'

#     return ret

# Read the database URI from the environment variable
DATABASE_URI = os.environ.get('DATABASE_URI', "postgresql://langflow_admin:gama24680@localhost:5432/langflow")

# Create a SQLAlchemy engine
engine = create_engine(DATABASE_URI)

# Create a MetaData object
metadata = MetaData()

# Define the table schema without using declarative_base
flow_table = Table(
    'flow',
    metadata,
    Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
    Column('user_id', UUID(as_uuid=True), nullable=False),
    Column('name', String, nullable=True),
    Column('data', JSON, nullable=False),
)

# Create a SQLAlchemy session
session = Session(engine)

def get_flow_by_name(name_param, max_retries=2, retry_delay=1):
    retries = 0
    while retries < max_retries:
        try:
            # Check if the name is provided
            if not name_param:
                return {'error': 'Name parameter is required'}, 400

            # Use SQLAlchemy ORM to query the database for the record based on the name field
            record = session.query(flow_table).filter_by(name=name_param).first()

            # Check if the record exists
            if not record:
                return {'error': 'Record not found'}, 404

            # Convert the record to a dictionary
            record_dict = {}
            for column in flow_table.columns:
                value = getattr(record, column.key)
                if isinstance(value, uuid.UUID):
                    record_dict[column.key] = str(value)
                else:
                    record_dict[column.key] = value

            return record_dict

        except Exception as e:
            logger.error(f"Error retrieving flow from the database: {str(e)}")
            retries += 1
            if retries < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                return {'error': str(e)}, 500

        finally:
            # Close the session in the 'finally' block to ensure it's closed regardless of success or failure
            session.close()

 
def main(context: Context):
    """ 
    Function template
    The context parameter contains the Flask request object and any
    CloudEvent received with the request.
    """
    
    try:
        # Add your business logic here
        print("Received request")
        print("Headers:\n", context.request.headers)
        print("Data:\n", context.request.get_data())
        event = from_http(context.request.headers, context.request.get_data())
        
        # Access cloudevent fields
        logger.info(
            f"Found {event['id']} from {event['source']} with type "
            f"{event['type']} and specversion {event['specversion']}"
        )

        # Validate CloudEvent type
        if event['type'] != "io.hitachivantara.langflow.execute.v1":
            return {'error': 'Invalid event type'}, 400

        # Retrieve flow JSON from the database based on the event data's name
        flow_json = get_flow_by_name(event.data.get('name', ''))
        logger.info("Flow JSON: %s", flow_json)

        # Load the flow using langflow
        flow = load_flow_from_json(flow_json, tweaks=event.data.get('tweaks', {}))

        # Use the flow like any chain
        inputs = event.data.get('inputs', {'input': ""})
        result = flow(inputs)

        # Create a Flask JSON response
        response = jsonify(result)

        # Add cloudevent headers to the response
        response.headers['Ce-Id'] = str(uuid.uuid4())
        response.headers['Ce-Source'] = 'langflow_function'
        response.headers['Ce-Specversion'] = '1.0'
        response.headers['Ce-Type'] = 'io.hitachivantara.langflow.execute.result.v1'
        response.headers['Content-Type'] = 'application/json'

        return response
    
    except Exception as err:
        return {'error': str(err)}, 500
