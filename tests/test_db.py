import pytest
from unittest.mock import patch, MagicMock
from utils import db

def test_get_engine_returns_engine():
    with patch("utils.db.create_engine") as mock_engine:
        mock_instance = MagicMock()
        mock_engine.return_value = mock_instance
        engine = db.get_engine()
        assert engine == mock_instance

def test_get_metadata_returns_metadata():
    with patch("utils.db.MetaData", return_value=MagicMock()) as mock_metadata:
        metadata = db.get_metadata()
        # Assert MetaData() constructor was called
        mock_metadata.assert_called_once()
        assert metadata is not None

def test_get_table_known():
    mock_table = MagicMock()
    with patch("utils.db.get_table", return_value=mock_table):
        table = db.get_table("employees")
        assert table == mock_table

def test_get_table_unknown_raises():
    with patch("utils.db.get_table", side_effect=KeyError):
        with pytest.raises(KeyError):
            db.get_table("nonexistent_table")
