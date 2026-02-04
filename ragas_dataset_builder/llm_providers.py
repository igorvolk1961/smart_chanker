"""
Модуль для работы с различными LLM провайдерами
"""

from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
import os


class LLMProvider:
    """Базовый класс для работы с LLM провайдерами"""
    
    @staticmethod
    def create_llm(config: Dict[str, Any]) -> BaseChatModel:
        """
        Создает LLM экземпляр на основе конфигурации
        
        Args:
            config: Конфигурация LLM из config.json
            
        Returns:
            Экземпляр LLM
        """
        provider = config.get("provider", "deepseek").lower()
        
        if provider == "deepseek":
            return LLMProvider._create_deepseek(config)
        elif provider == "qwen":
            return LLMProvider._create_qwen(config)
        elif provider == "glm":
            return LLMProvider._create_glm(config)
        else:
            raise ValueError(f"Неподдерживаемый провайдер: {provider}")
    
    @staticmethod
    def _create_deepseek(config: Dict[str, Any]) -> BaseChatModel:
        """Создает DeepSeek LLM"""
        api_key = config.get("api_key") or os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DeepSeek API key не найден. Установите в config.json или DEEPSEEK_API_KEY")
        
        base_url = config.get("base_url", "https://api.deepseek.com")
        model = config.get("model", "deepseek-chat")
        temperature = config.get("temperature", 0.7)
        max_tokens = config.get("max_tokens", 2000)
        
        return ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    
    @staticmethod
    def _create_qwen(config: Dict[str, Any]) -> BaseChatModel:
        """Создает Qwen LLM через OpenAI-совместимый API DashScope"""
        api_key = config.get("api_key") or os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("DashScope API key не найден. Установите в config.json или DASHSCOPE_API_KEY")
        
        # Используем OpenAI-совместимый endpoint DashScope
        # По умолчанию используем сингапурский endpoint, можно переопределить в config
        base_url = config.get(
            "base_url", 
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
        )
        model = config.get("model", "qwen-turbo")
        temperature = config.get("temperature", 0.7)
        max_tokens = config.get("max_tokens", 2000)
        
        return ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    
    @staticmethod
    def _create_glm(config: Dict[str, Any]) -> BaseChatModel:
        """
        Создает GLM LLM.
        Поддерживает два режима:
        1. Официальный ZhipuAI API (через zhipuai SDK)
        2. OpenAI-совместимый API через сторонние платформы (если указан base_url)
        """
        api_key = config.get("api_key") or os.getenv("ZHIPUAI_API_KEY")
        if not api_key:
            raise ValueError("ZhipuAI API key не найден. Установите в config.json или ZHIPUAI_API_KEY")
        
        model = config.get("model", "glm-4")
        temperature = config.get("temperature", 0.7)
        max_tokens = config.get("max_tokens", 2000)
        base_url = config.get("base_url")
        
        # Если указан base_url, используем OpenAI-совместимый API
        if base_url:
            return ChatOpenAI(
                model=model,
                openai_api_key=api_key,
                openai_api_base=base_url,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        
        # Иначе используем официальный ZhipuAI SDK
        try:
            from langchain_community.chat_models import ChatZhipuAI
        except ImportError:
            raise ImportError(
                "Для использования GLM через официальный API требуется zhipuai. "
                "Установите: pip install zhipuai\n"
                "Или используйте OpenAI-совместимый API, указав base_url в конфиге."
            )
        
        return ChatZhipuAI(
            model=model,
            zhipuai_api_key=api_key,
            temperature=temperature,
        )


class EmbeddingProvider:
    """Класс для работы с embedding моделями"""
    
    @staticmethod
    def create_embeddings(config: Dict[str, Any]):
        """
        Создает embedding модель на основе конфигурации
        
        Args:
            config: Конфигурация embeddings из config.json
            
        Returns:
            Экземпляр embedding модели
        """
        provider = config.get("provider", "openai").lower()
        
        if provider == "openai":
            return EmbeddingProvider._create_openai_embeddings(config)
        elif provider == "qwen":
            return EmbeddingProvider._create_qwen_embeddings(config)
        else:
            raise ValueError(f"Неподдерживаемый провайдер embeddings: {provider}")
    
    @staticmethod
    def _create_openai_embeddings(config: Dict[str, Any]):
        """Создает OpenAI embeddings"""
        from langchain_openai import OpenAIEmbeddings
        
        api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key не найден для embeddings")
        
        model = config.get("model", "text-embedding-3-small")
        
        return OpenAIEmbeddings(
            model=model,
            openai_api_key=api_key,
        )
    
    @staticmethod
    def _create_qwen_embeddings(config: Dict[str, Any]):
        """Создает Qwen embeddings через DashScope"""
        try:
            from langchain_community.embeddings import DashScopeEmbeddings
        except ImportError:
            raise ImportError(
                "Для использования Qwen embeddings требуется dashscope. "
                "Установите: pip install dashscope"
            )
        
        api_key = config.get("api_key") or os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("DashScope API key не найден для embeddings")
        
        model = config.get("model", "text-embedding-v2")
        
        return DashScopeEmbeddings(
            model=model,
            dashscope_api_key=api_key,
        )

