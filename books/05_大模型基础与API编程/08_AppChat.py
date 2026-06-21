import os
import sys

import markdown
from dotenv import load_dotenv
from openai import OpenAI
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLineEdit, QMainWindow, QPushButton
from PySide6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget

# 读取本地 .env 或终端中的环境变量，避免把 API Key 写进代码。
load_dotenv()
API_KEY = os.getenv("ZAI_API_KEY")
MODEL_NAME = "glm-5.2"
SYSTEM_PROMPT = (
    "你是一个通用学习助手。回答要简洁，注重原理阐释和示例引导；"
    "优先通过苏格拉底式提问启发用户思考。返回格式使用 Markdown。"
)

client = OpenAI(api_key=API_KEY or "missing", base_url="https://open.bigmodel.cn/api/paas/v4/")


class Worker(QObject):
    """在后台线程中流式调用大模型，避免阻塞 GUI 主线程。"""

    # 后台线程通过信号把中间输出、最终结果和错误通知给 GUI 主线程。
    delta = Signal(str)
    done = Signal(str)
    error = Signal(str)

    def __init__(self, messages):
        super().__init__()
        self.messages = messages

    def run(self):
        try:
            answer = ""
            stream = client.chat.completions.create(
                model=MODEL_NAME, messages=self.messages, temperature=0.6, stream=True
            )
            for chunk in stream:
                answer += chunk.choices[0].delta.content or ""
                self.delta.emit(answer)
            self.done.emit(answer)
        except Exception as exc:
            self.error.emit(str(exc))


class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GLM Chat Demo")
        self.resize(900, 700)
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]

        # QTextBrowser 显示 HTML；Markdown 先转 HTML，代码块和表格更稳定。
        self.view = QTextBrowser(openExternalLinks=True)
        self.input = QLineEdit(placeholderText="输入问题，按 Enter 发送")
        self.button = QPushButton("发送")
        row = QHBoxLayout()
        row.addWidget(self.input)
        row.addWidget(self.button)
        layout = QVBoxLayout()
        layout.addWidget(self.view)
        layout.addLayout(row)
        root = QWidget(); 
        root.setLayout(layout); 
        self.setCentralWidget(root)
        self.input.returnPressed.connect(self.send)
        self.button.clicked.connect(self.send)

    def render(self, partial=""):
        """把历史消息和当前流式片段渲染为 Markdown。"""
        blocks = []
        for msg in self.history[1:]:
            name = "你" if msg["role"] == "user" else "助手"
            blocks.append(f"### {name}\n\n{msg['content']}")
        if partial:
            blocks.append(f"### 助手\n\n{partial}")
        body = markdown.markdown(
            "\n\n---\n\n".join(blocks), extensions=["fenced_code", "tables"]
        )
        self.view.setHtml(f"<style>pre{{background:#f6f8fa;padding:8px;}}</style>{body}")

    def send(self):
        question = self.input.text().strip()
        if not question:
            return
        if not API_KEY:
            self.view.setHtml("请先设置环境变量 <code>ZAI_API_KEY</code>。")
            return
        self.input.clear()
        self.input.setEnabled(False)
        self.button.setEnabled(False)
        self.history.append({"role": "user", "content": question})
        self.render()

        # 每次发送都启动一个后台线程；模型 token 到达时通过 Signal 更新界面。
        self.thread = QThread()
        self.worker = Worker(self.history.copy())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.delta.connect(self.render)
        self.worker.done.connect(self.finish)
        self.worker.error.connect(lambda e: self.finish(f"调用失败：`{e}`"))
        self.worker.done.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.start()

    def finish(self, answer):
        self.history.append({"role": "assistant", "content": answer})
        self.input.setEnabled(True)
        self.button.setEnabled(True)
        self.render()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ChatWindow()
    win.show()
    sys.exit(app.exec())
