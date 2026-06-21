import os

import gradio as gr
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

api_key = os.getenv("ZAI_API_KEY")

client = OpenAI(
    api_key=api_key or "missing",
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)
MODEL_NAME = "glm-5.2"
SYSTEM_PROMPT = (
    "你是一个通用学习助手。回答要简洁，注重原理阐释和示例引导；"
    "优先通过苏格拉底式提问启发用户思考。可以使用 Markdown。"
)


def to_messages(message: str, history: list) -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in history:
        if isinstance(item, dict):
            messages.append({"role": item["role"], "content": item["content"]})
        else:
            user, assistant = item
            messages.append({"role": "user", "content": user})
            messages.append({"role": "assistant", "content": assistant})
    messages.append({"role": "user", "content": message})
    return messages


def chat(message: str, history: list):
    if not api_key:
        yield "请先设置环境变量 `ZAI_API_KEY`。"
        return

    stream = client.chat.completions.create(
        model=MODEL_NAME,
        messages=to_messages(message, history),
        temperature=0.6,
        stream=True,
    )

    answer = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        answer += delta
        yield answer


demo = gr.ChatInterface(
    fn=chat,
    title="GLM Chat Demo",
    description="支持多轮对话、流式输出和 Markdown 展示。",
)


if __name__ == "__main__":
    demo.launch()
