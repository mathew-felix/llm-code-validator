import openai


def main():
    return openai.ChatCompletion.create(model="gpt-4o-mini", messages=[])
