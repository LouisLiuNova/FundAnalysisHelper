import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


@dataclass
class LLMConfig:
    base_url: str
    api_key: str
    analyst_model: str
    debater_model: str
    report_model: str
    temperature: float = 0.3
    max_tokens: int = 16384


@dataclass
class MongoDBConfig:
    uri: str
    database: str = "fund_analysis"


@dataclass
class RedisConfig:
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = ""


@dataclass
class TushareConfig:
    token: str


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000


@dataclass
class Config:
    llm: LLMConfig
    mongodb: MongoDBConfig
    redis: RedisConfig
    tushare: TushareConfig
    server: ServerConfig


_VAR_RE = re.compile(r"\$\{(\w+)\}")


def _resolve_env(value: str) -> str:
    match = _VAR_RE.fullmatch(value.strip())
    if match:
        return os.environ.get(match.group(1), "")
    return value


def load_config(path: str | None = None) -> Config:
    if path is None:
        path = Path(__file__).parent.parent.parent / "config.yaml"
    with open(path) as f:
        raw = yaml.safe_load(f)

    return Config(
        llm=LLMConfig(
            base_url=raw["llm"]["base_url"],
            api_key=_resolve_env(raw["llm"]["api_key"]),
            analyst_model=raw["llm"]["analyst_model"],
            debater_model=raw["llm"]["debater_model"],
            report_model=raw["llm"]["report_model"],
            temperature=raw["llm"].get("temperature", 0.3),
            max_tokens=raw["llm"].get("max_tokens", 16384),
        ),
        mongodb=MongoDBConfig(
            uri=raw["mongodb"]["uri"],
            database=raw["mongodb"].get("database", "fund_analysis"),
        ),
        redis=RedisConfig(
            host=raw["redis"].get("host", "localhost"),
            port=raw["redis"].get("port", 6379),
            db=raw["redis"].get("db", 0),
            password=raw["redis"].get("password", ""),
        ),
        tushare=TushareConfig(token=_resolve_env(raw["tushare"]["token"])),
        server=ServerConfig(
            host=raw.get("server", {}).get("host", "0.0.0.0"),
            port=raw.get("server", {}).get("port", 8000),
        ),
    )
