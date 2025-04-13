import os
# import readline  # 提供输入历史支持（Unix系统）
from typing import List, Dict
from dk_client import LocalLLMClient, LocalLLMConfig  # 引用之前定义的客户端


class ChatSession:
    """对话会话管理（支持上下文保持）"""

    def __init__(self, client: LocalLLMClient):
        self.client = client
        self.history: List[Dict[str, str]] = []
        self.exit_commands = {"exit", "quit", "q"}

    def _print_welcome(self):
        """显示欢迎信息"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("""\033[34m
        DeepSeek 本地交互终端（版本 1.1）
        输入您的消息，模型将实时响应
        支持多行输入（以空行结束），输入 help 查看命令\033[0m
        """)

    def _get_user_input(self) -> str:
        """获取多行用户输入（支持空行结束）"""
        print("\033[32m[用户]\033[0m ", end="")
        lines = []
        line = input()
        if not line.strip() == "":
            lines.append(line)

        return "\n".join(lines)

    def _process_special_commands(self, input_text: str) -> bool:
        """处理特殊命令"""
        cmd = input_text.strip().lower()
        if cmd in self.exit_commands:
            print("\033[33m会话结束，感谢使用！\033[0m")
            return True
        if cmd == "help":
            print("\033[36m可用命令：")
            print("  help    - 显示帮助信息")
            print("  history - 显示对话历史")
            print("  clear   - 清空对话历史")
            print("  exit    - 退出程序\033[0m")
            return True
        if cmd == "history":
            self._show_history()
            return True
        if cmd == "clear":
            self.history.clear()
            print("\033[33m历史记录已清空\033[0m")
            return True
        return False

    def _show_history(self):
        """显示对话历史"""
        print("\033[35m\n--- 对话历史 ---")
        for idx, msg in enumerate(self.history, 1):
            role = msg["role"]
            color = "\033[32m" if role == "user" else "\033[34m"
            print(f"{color}[{role.capitalize()} #{idx}]\033[0m")
            print(msg["content"] + "\n")
        print("---------------\033[0m")

    def run(self):
        """启动交互循环"""
        self._print_welcome()

        while True:
            try:
                # 获取用户输入
                user_input = self._get_user_input()

                # 处理空输入
                if not user_input.strip():
                    continue

                # 处理特殊命令
                if self._process_special_commands(user_input):
                    continue

                # 构建对话上下文
                self.history.append({"role": "user", "content": user_input})

                # 发送请求并显示加载状态
                print("\033[34m[系统] 模型生成中...\033[0m")
                response = next(self.client.generate(
                    messages=self.history,
                    # temperature=0.3  # 降低随机性以获得更稳定输出
                ))

                # 解析并显示响应
                reply = response['message']['content']
                print(f"\033[34m[DeepSeek]\033[0m\n{reply}\n")

            except KeyboardInterrupt:
                print("\n\033[33m检测到中断，输入 'exit' 退出程序\033[0m")
            except Exception as e:
                print(f"\033[31m[系统错误] {str(e)}\033[0m")


if __name__ == "__main__":
    # 初始化客户端
    config = LocalLLMConfig(
        endpoint="http://localhost:11434/api/chat",
        timeout=90
    )
    client = LocalLLMClient(config)

    # 启动会话
    session = ChatSession(client)
    session.run()
