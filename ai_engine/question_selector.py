import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_mcqs(topic, n=3):
    prompt = f"Create {n} multiple choice questions with options and correct answer for the topic '{topic}' suitable for 10th/12th student."
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"user","content":prompt}],
        temperature=0.7,
        max_tokens=400
    )
    # You can parse response to JSON or keep as text
    return response.choices[0].message.content.strip()