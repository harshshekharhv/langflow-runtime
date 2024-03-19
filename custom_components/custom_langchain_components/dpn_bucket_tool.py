from langchain.tools import BaseTool

import boto3
import re
from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain.tools import BaseTool
from custom_components.custom_langchain_components.seldon_wrapper import SeldonCore

llm = SeldonCore(repo_id= "sqlcoder-7b-gpu", endpoint_url="http://seldon-mesh.genai.sc.eng.hitachivantara.com",
            task="text2text-generation",
            model_kwargs={
                    "temperature": 0.4,
                    "top_p": 0.15,
                    "top_k": 0,
                    "repetition_penalty": 1.1,
                    "max_new_tokens": 1000
                }, verbose=True)


# special tokens used by llama 2 chat
B_INST, E_INST = "[INST]", "[/INST]"
B_SYS, E_SYS = "<<SYS>>\n", "\n<</SYS>>\n\n"

sys_msg = "<s>" + B_SYS + """Assistant is a expert JSON builder designed to assist with a wide range of tasks.

Assistant is able to respond to the User and use tools using JSON strings that contain "action" and "action_input" parameters.

All of Assistant's communication is performed using this JSON format.

Assistant can also use tools by responding to the user with tool use instructions in the same "action" and "action_input" JSON format. Tools available to Assistant are:

- "List_dpn_bucket_content_tool": Useful for when you want to list the contents of a s3 bucket.
  - To use the List_dpn_bucket_content_tool tool, Assistant should write like so:
    ```json
    {{"action": "List_dpn_bucket_content_tool","action_input": "bucket_name"}}
    ```
- "SQL_tool": Useful to query dpn database.
  - To use the SQL_tool tool, Assistant should write like so:
    ```json
    {{"action": "SQL_tool","action_input": "query"}}
    ```

When Assistant responds with JSON they make sure to enclose the JSON with three back ticks.

Important - When ever there is Observation in context, check observation results if they can be used to answer the initial question and reply in below format -

Assistant: ```json
{{"action": "Final Answer",
 "action_input": "Answer of the initial question"}}
\```
Important - In action Final Answer, the action_input should be in human readable form. Enhance the observation results in readable format.
Here are some previous conversations between the Assistant and User:

User: Can you list the contents of the following bucket?

Assistant: ```json
{{

  "action": "List_dpn_bucket_content_tool",

  "action_input": "test"

}}\```
User: Observation - results [mk.pdf, cpp.pdf]
Assistant: ```json
{{"action": "Final Answer",
 "action_input": "the bucket contents are [mk.pdf, cpp.pdf] "}}
\```
Another example for SQL tool - 
User: Can you list all the customers from table?
Assistant: ```json
{{

  "action": "SQL_tool",

  "action_input": "select * from customers"

}}\```
User: Observation - results [Harsha Bodda].
Assistant: ```json
{{"action": "Final Answer",
 "action_input": "the query results are as follows : 'Harsha Bodda'"}}
\```


Here is the latest conversation between Assistant and User.""" + E_SYS

instruction = B_INST + " Use your existing tools and respond with a JSON object with with 'action' and 'action_input' values. Note - Never respond in any other format otherwise agent will throw exception. " + E_INST
human_msg = instruction + "\nUser: {input}\n\n{agent_scratchpad}"




class ListDpnBucketContentTool(BaseTool):
    name = "List_dpn_bucket_content_tool"
    description = """
        Accepts only bucket name as string. For example if bucket name is demo, then input will be demo.
        Returns the list of items under the given bucket.
        """

    def _run(self, bucketName: str):
        """
        Returns the list of items under the given bucket.
        """
        objects = []
        bucketNames = []
        bucket_name=bucketName.strip("\'")
        try:
            session = boto3.session.Session()

            client = session.client(
                service_name='s3',
                aws_access_key_id='dpnaccesskeyid',
                aws_secret_access_key='dpnsecretaccesskey',
                verify=False,
                endpoint_url='https://dpn-engine.genai.sc.eng.hitachivantara.com')
            res = client.list_objects(Bucket=bucket_name)
            print('response -- ', res)
            file = None
            objects = res.get('Contents', [])
            for obj in objects:
                print(obj['Key'])
                bucketNames.append(obj['Key'])
            #bucketNames=res['Buckets']
        except Exception as e:
            print(f"An error occurred: {type(e).__name__} - {e}")
        return {"results": bucketNames}

    def _arun(self, bucket: str):
        raise NotImplementedError("This tool does not support async")
    
class SqlTool(BaseTool):
    name = "SQL_tool"
    description = "use this tool to query dpn database"
    handle_tool_error = True
    def _run(self, query: str):
        
        try:
            token= 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJERUZBVUxUX05PTl9BVVRIRU5USUNBVEVEX1VTRVJfSUQiLCJleHAiOjE3MTI5NzgwOTN9.2rfCH3PdPIxjAVwkvIAi8Vmu4IK5FllPi452St53yWU'
            db = SQLDatabase.from_uri(f"dpn+flightsql://dpn-engine-grpc.genai.sc.eng.hitachivantara.com:80?token={token}") 
            
            # chain = create_sql_query_chain(llm, db)
            # response = chain.invoke({"question": query})
            print('reponse -- ', query)
            generated_text = db.run(query)
            
            print(generated_text)
            final_output = self.parse_string_to_list(generated_text)
            return {"results": final_output}
            
        except Exception as e:
            print(f"Execption occured -- {e}")
            raise e
    def _arun(self, radius: int):
        raise NotImplementedError("This tool does not support async")
    
    def parse_string_to_list(self,sql_output_string) -> str:

        # Input SQL query output string
        #sql_output_string = "[('kiwi', 'gw', 1803222, 3662547, 1459516, datetime.datetime(2024, 1, 17, 0, 0), datetime.datetime(2024, 1, 17, 23, 59, 59)), ('kiwi', '', 1803222, 3662547, 1459516, datetime.datetime(2024, 1, 17, 0, 0), datetime.datetime(2024, 1, 17, 23, 59, 59)), ('pear', 'gw', 99172, 278571, 0, datetime.datetime(2024, 1, 17, 0, 0), datetime.datetime(2024, 1, 17, 23, 59, 59))]"

        output_string = re.sub(r"datetime\.datetime\([^)]*\)", "", sql_output_string)

        # Remove any leftover trailing commas or spaces
        output_string = re.sub(r",\s*$", "", output_string)

        print(output_string)
        return output_string