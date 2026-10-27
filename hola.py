import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://api.meta.ai/v1",
    api_key=os.environ["MODEL_API_KEY"],
)

respuesta = client.responses.create(
    model="muse-spark-1.3",
    input="Hola Muse, preséntate en una frase en español.",
)

print(respuesta.output_text)
