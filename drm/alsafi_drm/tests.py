from django.test import TestCase

# Create your tests here.
from openai import OpenAI

client = OpenAI(
    api_key="",
    base_url="https://api.together.xyz/v1"
)

response = client.chat.completions.create(
    model="Qwen/Qwen3-Next-80B-A3B-Instruct",
    messages=[{"role": "user", "content": "Привет, как дела?"}]
)

print(response.choices[0].message.content)
