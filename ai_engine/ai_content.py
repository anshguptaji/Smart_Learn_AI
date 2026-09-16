import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_content(topic):
    prompt = f"Explain the topic '{topic}' in simple, beginner-friendly language for a 10th/12th student."
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"user","content":prompt}],
        temperature=0.7,
        max_tokens=500
    )
    return response.choices[0].message.content.strip()