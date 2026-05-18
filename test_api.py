from dotenv import dotenv_values
from pathlib import Path
import anthropic

env = dotenv_values(Path(__file__).parent / ".env")

client = anthropic.Anthropic(api_key=env["ANTHROPIC_API_KEY"])

message = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=64,
    messages=[{"role": "user", "content": "Say 'Rinata API connection successful!' and nothing else."}]
)

print(message.content[0].text)
