import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

api_key = os.getenv("ZAI_API_KEY")
if not api_key:
    raise RuntimeError("请先设置环境变量 ZAI_API_KEY")

client = OpenAI(
    api_key=api_key,
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)
MODEL_NAME = "glm-5.2"
SYSTEM_PROMPT = (
    "你是一个通用学习助手。回答要简洁，注重原理阐释和示例引导；"
    "优先通过苏格拉底式提问启发用户思考。"
)

messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
]


def ask(user_input: str) -> str:
    messages.append({"role": "user", "content": user_input})
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.6,
    )
    answer = response.choices[0].message.content
    messages.append({"role": "assistant", "content": answer})
    return answer


def main() -> None:
    print("CmdChat 已启动。输入 exit 或 quit 退出。")
    while True:
        user_input = input("\n你：").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue
        print(f"\n助手：{ask(user_input)}")


if __name__ == "__main__":
    main()
