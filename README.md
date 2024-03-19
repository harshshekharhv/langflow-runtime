# langflow-runtime

A Knative function exposing an API to run custom flows of Langflow via flow names.

## Endpoints

Running this function will expose three endpoints.

  * `/` The endpoint for running a flow via langflow-runtime.
  * `/health/readiness` The endpoint for a readiness health check
  * `/health/liveness` The endpoint for a liveness health check

The health checks can be accessed in your browser at
[http://localhost:8080/health/readiness]() and
[http://localhost:8080/health/liveness]().

You can use `func invoke` to send an HTTP request to the function endpoint.

## Examples

Here's a sample custom flow json [DPN_TOOLS](./examples/multiple_tools_flow.json) and a sample curl request for running the flow:

```sh
curl --location 'http://0.0.0.0:8080' \
--header 'Ce-Id: akgagfkagfk' \
--header 'Ce-Source: 64d10f880ada2fb213b3c0a2' \
--header 'Ce-Specversion: 1.0' \
--header 'Ce-Type: io.hitachivantara.langflow.execute.v1' \
--header 'Content-Type: application/json' \
--data '{
    "name": "DPN SQL flow",
    "inputs": {
        "input": "Get all tenants from table chargebacktenant only 10 records"   
    },
    "tweaks": {
        "SeldonCore-wBvtJ": {},
        "ConversationBufferWindowMemory-LbpEx": {},
        "DpnSqlAgentIntializer-pLLFl": {},
        "S3Bucket-rVqUs": {},
        "SQLTool-XuLwm": {}
    }
}'
```


## Testing

This function project includes a [unit test](./test_func.py). Update this
as you add business logic to your function in order to test its behavior.

```console
python test_func.py
```
