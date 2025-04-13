import json
import logging
from typing import Dict, Any, Generator, Optional
from pydantic import BaseModel, field_validator, ValidationError
import requests
from requests.exceptions import RequestException

# 配置结构化日志（优化日志格式）
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(name)s - [%(filename)s:%(lineno)d] - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("__name__")


class LocalLLMConfig(BaseModel):
    """本地大语言模型配置类（兼容Ollama API标准）

    属性：
    endpoint: 模型服务端点地址，默认使用Ollama标准API路径
    model_name: 模型名称，必须与Ollama拉取的模型名称完全一致
    timeout: 请求超时时间（秒），本地模型建议适当延长
    max_retries: 最大重试次数，针对网络波动的容错机制
    temperature: 生成温度参数，范围[0.0, 2.0]
    """
    endpoint: str = "http://localhost:11434/api/chat"
    model_name: str = "deepseek-r1:1.5b"
    timeout: int = 300
    max_retries: int = 3
    temperature: float = 0.7

    @field_validator("endpoint")
    def validate_endpoint(cls, value: str) -> str:
        """验证端点地址格式"""
        if not value.startswith(("http://", "https://")):
            raise ValueError("端点协议必须为http或https")
        return value.rstrip('/')  # 去除末尾可能存在的斜杠

    @field_validator("temperature")
    def validate_temperature(cls, value: float) -> float:
        """验证温度参数有效性"""
        if not 0.0 <= value <= 2.0:
            raise ValueError("温度参数必须在[0.0, 2.0]范围内")
        return value


class LocalLLMClient:
    """Ollama大语言模型客户端（支持标准/流式响应）

    功能：
    - 自动创建带重试机制的HTTP会话
    - 处理请求/响应数据格式转换
    - 异常处理和日志记录
    """

    def __init__(self, config: Optional[LocalLLMConfig] = None):
        """初始化客户端
        Args:
            config: 可选配置对象，默认使用默认配置
        """
        self.config = config or LocalLLMConfig()  # 避免使用可变默认值
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """创建带连接池和重试机制的HTTP会话"""
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            max_retries=self.config.max_retries,
            pool_connections=10,  # 连接池大小
            pool_maxsize=100  # 最大连接数
        )
        # 为HTTP和HTTPS注册适配器
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def generate(
            self,
            messages: list[dict],
            stream: bool = False,
            **kwargs
    ) -> Generator[Dict[str, Any], None, None]:
        """执行生成请求
        Args:
            messages: 对话历史，格式示例：
                [{"role": "user", "content": "你好"}]
            stream: 是否使用流式响应模式
            **kwargs: 额外请求参数（将合并到请求体中）

        Yields:
            字典格式的响应数据

        Raises:
            APIConnectionError: 网络或API连接问题
            ValidationError: 配置验证失败
        """
        # 构建符合Ollama API规范的请求体（优化参数合并）
        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "stream": stream,
            **kwargs  # 允许覆盖或添加额外参数
        }

        logger.debug(f"请求端点：{self.config.endpoint}")
        logger.debug(f"请求参数：{json.dumps(payload, indent=2, ensure_ascii=False)}")

        try:
            with self.session.post(
                    url=self.config.endpoint,
                    json=payload,
                    timeout=self.config.timeout,
                    stream=stream  # 流式模式需要保持连接
            ) as response:
                response.raise_for_status()  # 触发HTTP错误状态码异常

                if stream:
                    yield from self._handle_stream(response)
                else:
                    yield self._handle_standard(response)

        except RequestException as re:
            error_msg = f"请求失败：{str(re)}"
            logger.error(error_msg, exc_info=True)
            raise APIConnectionError(error_msg) from re
        except ValidationError as ve:
            logger.error("配置验证失败", exc_info=True)
            raise

    def _handle_standard(self, response: requests.Response) -> Dict[str, Any]:
        """处理标准（非流式）响应
        Returns:
            解析后的JSON响应字典

        Raises:
            ValueError: 响应格式不符合预期
            JSONDecodeError: JSON解析失败
        """
        try:
            data = response.json()
            # 验证必要字段存在（增强健壮性）
            if "message" not in data or "content" not in data["message"]:
                logger.error(f"无效响应格式：{json.dumps(data, indent=2)}")
                raise ValueError("响应缺少必要字段")
            return data
        except json.JSONDecodeError as je:
            logger.error(f"JSON解析失败，原始响应：{response.text[:200]}...")
            raise

    def _handle_stream(self, response: requests.Response) -> Generator[Dict[str, Any], None, None]:
        """处理流式响应
        Yields:
            每个数据块对应的字典

        Raises:
            StreamInterruptionError: 流传输中断
        """
        try:
            for raw_line in response.iter_lines():
                # 过滤心跳保持连接的空行
                if raw_line:
                    try:
                        line = raw_line.decode('utf-8').strip()
                        chunk = json.loads(line)
                        # 验证数据块有效性
                        if "message" in chunk and "content" in chunk["message"]:
                            yield chunk
                        else:
                            logger.debug(f"收到元数据块：{chunk}")
                    except json.JSONDecodeError:
                        logger.warning(f"无效JSON数据：{line}")
        except requests.exceptions.ChunkedEncodingError as ce:
            error_msg = f"流传输中断：{str(ce)}"
            logger.error(error_msg)
            raise StreamInterruptionError(error_msg) from ce


class APIConnectionError(Exception):
    """自定义API连接异常（用于网络/服务器错误）"""

    def __init__(self, message: str):
        super().__init__(f"[API连接异常] {message}")


class StreamInterruptionError(Exception):
    """自定义流式传输中断异常"""

    def __init__(self, message: str):
        super().__init__(f"[流中断] {message}")


# 测试用例
if __name__ == "__main__":
    # 测试代码
    try:
        # 初始化配置（示例使用自定义参数）
        config = LocalLLMConfig(
            endpoint="http://localhost:11434/api/chat",
            model_name="deepseek-r1:1.5b",
            temperature=0.5  # 调低随机性
        )

        client = LocalLLMClient(config)

        # 执行标准请求
        response = client.generate(
            messages=[{"role": "user", "content": "量子纠缠的基本原理是什么？"}]
        )
        result = next(response)

        # 处理响应（增加健壮性检查）
        if "message" in result and "content" in result["message"]:
            print("\n[模型回复]".ljust(20, '='))
            print(result["message"]["content"])
        else:
            logger.error("响应格式异常", extra={"response": result})

    except APIConnectionError as e:
        logger.error(f"连接失败：{str(e)}")
    except Exception as e:
        logger.error(f"未处理异常：{str(e)}", exc_info=True)
