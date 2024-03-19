import json
import logging
from typing import Any, Dict, List, Mapping, Optional, Union

import requests
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.embeddings.base import Embeddings
from langchain.llms.base import LLM
from langchain.llms.utils import enforce_stop_tokens
from langchain.utils import get_from_dict_or_env
from pydantic.v1 import Extra, root_validator

logger = logging.getLogger(__name__)

DEFAULT_REPO_ID = "llama2-chat"
VALID_TASKS = (
    "text-generation",
    "text2text-generation",
    "summarization",
    "question-answering",
)

DEFAULT_CONFIG = {
    "top_k": 0,
    "top_p": 0.15,
    "temperature": 0.1,
    "repetition_penalty": 1.1,
    "max_new_tokens": 64,
}


def encode_request(payload: Dict) -> Dict[str, Any]:
    # I don't want to bring in all the mlserver mlserver-huggingface transitives
    # just to be able to use the huggingface codecs to correctly parse the
    # payload.  So here is a stripped version of the MLServer hf codec.
    # https://github.com/SeldonIO/MLServer/blob/d86bbb590892fa344808061abd56c0b13969158f/docs/examples/huggingface/README.md
    inputs = []
    for name, value in payload.items():
        inputs.append({
            "name": name,
            "shape": [-1],  # -1 seems to work for most cases
            "datatype": "BYTES",
            "parameters": {
                # TODO: str or raw, other types allowed?
                "content_type": "str" if isinstance(value, (str, )) else "raw"
            },
            "data": [value]
        })
    return {
        "parameters": {
            "context_type": "hf"
        },
        "inputs": inputs,
    }


class InferenceApi:
    """Client to configure requests and make calls to the Seldon V2 API."""
    def __init__(
        self,
        repo_id: str,
        task: Optional[str] = None,
        url: Optional[str] = None,
    ):
        """Inits headers and API call information."""
        self.headers = {
            "Content-Type": "application/json",
            "Seldon-Model": repo_id,
        }
        self.task = task
        self.session = requests.Session()
        self.session.headers = self.headers
        self.api_url = f"{url}/v2/models/model/infer"

    def __call__(
        self,
        inputs: Optional[Union[str, Dict, List[str], List[List[str]]]] = None,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        raw_response: bool = False,
    ) -> Any:
        """Make a call to the inference API."""
        if self.task == "question-answering":
            request = {"question": inputs[0], "context": inputs[1]}
        else:
            request = {"array_inputs": inputs}
        if params is None:
            params = {}
        request.update(params)
        payload = encode_request(request)
        response = self.session.post(self.api_url, json=payload, data=data)
        response.raise_for_status()

        logger.debug(response)

        if raw_response:
            return response

        content_type = response.headers.get("Content-Type") or ""
        if content_type == "application/json":
            return response.json()
        if content_type == "text/plain":
            return response.text
        raise NotImplementedError(
            f"{content_type} output type is not implemented yet.  You can pass"
            " `raw_response=True` to get the raw `Response` object and parse the"
            " output yourself."
        )


class SeldonCore(LLM, Embeddings):
    """Seldon Core Endpoint models.

    Example:
        .. code-block:: python
            from llm_seldon.langchain import SeldonCore

            endpoint_url = (
                    "http://0.0.0.0:9000"
            )
            llm = SeldonCore(
                repo_id="gpt2",
                endpoint_url=endpoint_url,
                model_kwargs={
                    "temperature": 0.1,
                    "max_length": 128,
                    "top_p": 0.15,
                    "top_k": 0,
                    "repetition_penalty": 1.1,
                }
            )
    """

    client: Any
    repo_id: str = DEFAULT_REPO_ID
    """Model name to use"""
    task: Optional[str] = None
    """Task to call the model with.
    Should be a task that returns `generated_text` or `summary_text`."""
    model_kwargs: Optional[dict] = None
    """key word arguments to pass to the model."""

    endpoint_url: Optional[str] = None

    class Config:
        """Configuration for this pydantic object."""
        extra = Extra.forbid

    @root_validator(pre=False, skip_on_failure=True)
    def validate_environment(cls, values: Dict) -> Dict:
        """Validate environment."""
        api_host = get_from_dict_or_env(
            values, "endpoint_url", "SELDON_ENDPOINT_URL"
        )
        repo_id = values["repo_id"]
        client = InferenceApi(repo_id, values.get('task'), api_host)
        values['client'] = client
        return values

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        """Get the identifying parameters."""
        _model_kwargs = self.model_kwargs or {}
        return {
            **{
                "repo_id": self.repo_id,
                "task": self.task
            },
            **{
                "model_kwargs": _model_kwargs
            },
        }

    @property
    def _llm_type(self) -> str:
        return "seldon_mlserver"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ):
        """Call out the Seldon API moder inference endpoint."""
        _model_kwargs = self.model_kwargs or {}
        params = {**_model_kwargs, **kwargs}
        response = self.client(inputs=prompt, params=params)
        if "error" in response:
            raise ValueError(
                f"Error raised by inference API: {response['error']}"
            )
        text = json.loads(response['outputs'][0]['data'][0])
        if self.client.task == "text-generation":
            # can only deal with first response
            text = text[0]['generated_text'][len(prompt):]
        elif self.client.task == "text2text-generation":
            text = text['generated_text']
        elif self.client.task == "summarization":
            text = text['summary_text']
        elif self.client.task == "question-answering":
            text = text['answer']
        else:
            raise ValueError(
                f"Got invalid task {self.client.task}, "
                f"currently only {VALID_TASKS} are supported"
            )
        if stop is not None:
            text = enforce_stop_tokens(text, stop)
        return text

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed search docs."""
        embeddings = []
        for text in texts:
            embeddings.append(self.embed_query(text))
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embed query text."""
        response = self.client(inputs=text)
        if "error" in response:
            raise ValueError(
                f"Error raised by inference API: {response['error']}"
            )
        embeddings = response['outputs'][0]['data']

        return embeddings
