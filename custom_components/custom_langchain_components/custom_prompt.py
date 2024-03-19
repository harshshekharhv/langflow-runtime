from langchain.prompts import StringPromptTemplate
from pydantic import Field


class CustomPromptTemplate(StringPromptTemplate):
    pre_prompt: str = Field(default='')
    context: str = Field(default='')
    template: str

    def format(self, **kwargs) -> str:
        kwargs['context'] = self.context
        kwargs['pre_prompt'] = self.pre_prompt
        return self.template.format(**kwargs)


if __name__ == "__main__":
    model_type = "llama2"

    template = ""
    if model_type == "llama2":
        template = template + "<s>[INST]<<SYS>>\n"
    template = template + "{pre_prompt}\n\nContext sections:\n{context}\n"
    if model_type == "llama2":
        template = template + "<</SYS>>"
    template = template + "\n\nCurrent conversation:\n{history}"
    if model_type == "llama2":
        template = template + "\n\n {input} [/INST]"
    else:
        template = template + "\n\nQuestion:\n{input}\n\nanswer:\n"

    # make sure you feed the PromptTemplate with the new variables
    prompt = CustomPromptTemplate(
        input_variables=["history", "input"], template=template, context="whatever", pre_prompt="test"
    )
