from unittest.mock import patch, MagicMock
from app.api.deps import get_analysis_service


def test_get_analysis_service_返回服务实例():
    with patch("app.api.deps.load_config") as mock_load, \
         patch("app.api.deps.AnalysisService") as mock_svc_cls:
        mock_cfg = MagicMock()
        mock_cfg.mongodb.uri = "mongodb://x"
        mock_cfg.mongodb.database = "db"
        mock_cfg.redis.host = "localhost"
        mock_cfg.redis.port = 6379
        mock_cfg.tushare.token = "token"
        mock_load.return_value = mock_cfg

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc

        svc = get_analysis_service()
        assert svc is mock_svc
