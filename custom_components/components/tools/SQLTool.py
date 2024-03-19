
from langflow import CustomComponent
from langchain.tools import BaseTool
from langchain.llms.base import BaseLLM
from langchain.tools.sql_database.tool import (
            # InfoSQLDatabaseTool,
            # ListSQLDatabaseTool,
            # QuerySQLCheckerTool,
            QuerySQLDataBaseTool,
        )
from custom_components.custom_langchain_components.dpn_bucket_tool import SqlTool
from typing import Dict, Optional, Union

class CustomSQLTool(CustomComponent):
    display_name: str = "DPN SQL Tool"
    description: str = "DPN SQL tool to query DPN database."
    beta = True
    
    def build_config(self):
        return { 
            # "query":{
            #     "required": True,
            #     "value": "Get all tenants from chargebacktenant only 10 records"
            #     },
            # "llm":{
            #     "required": True
            #     },
            # "DB_URI":{
            #     "required": True,
            #     "value": "dpn+flightsql://dpn-engine-grpc.genai.sc.eng.hitachivantara.com:80"
            #     },
            # "token":{
            #     "required": True,
            #     "value": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJERUZBVUxUX05PTl9BVVRIRU5USUNBVEVEX1VTRVJfSUQiLCJleHAiOjE3MTI5NzgwOTN9.2rfCH3PdPIxjAVwkvIAi8Vmu4IK5FllPi452St53yWU"
                # }
            }

    def build(self) -> Union[BaseTool, SqlTool]:
        sqlTool = SqlTool()
        # return sqlTool._run(query=query)
        # return sqlTool._run(query=query, llm=llm, DB_URI=DB_URI, token=token)
        return sqlTool
    # def build(self, query: str, llm: BaseLLM, DB_URI: str, token: str) -> str:
    #     sqlTool = SqlTool(query=query, llm=llm, DB_URI=DB_URI, token=token)
    #     # return sqlTool._run(query=query)
    #     return sqlTool._run(query=query, llm=llm, DB_URI=DB_URI, token=token)
    #     # return sqlTool

