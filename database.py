import os
import pymysql
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text

DEFAULT_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "port": int(os.environ.get("MYSQL_PORT", 3306)),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "database": os.environ.get("MYSQL_DB", "vnstock_db")
}

def get_db_config(user_config: dict = None) -> dict:
    """Returns a merged configuration dictionary."""
    config = DEFAULT_CONFIG.copy()
    if user_config:
        for k, v in user_config.items():
            if v is not None:
                config[k] = v
    return config

def get_mysql_connection(config: dict = None, include_db: bool = True):
    """Establishes a raw PyMySQL connection."""
    cfg = get_db_config(config)
    kwargs = {
        "host": cfg["host"],
        "port": int(cfg["port"]),
        "user": cfg["user"],
        "password": cfg["password"],
        "charset": "utf8mb4",
        "autocommit": True
    }
    if include_db and cfg.get("database"):
        kwargs["database"] = cfg["database"]
    return pymysql.connect(**kwargs)

def create_database_if_not_exists(config: dict = None):
    """Creates the target MySQL database if it does not exist."""
    cfg = get_db_config(config)
    db_name = cfg["database"]
    try:
        conn = get_mysql_connection(cfg, include_db=False)
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.close()
        return True, f"Database `{db_name}` created or already exists."
    except Exception as e:
        return False, f"Failed to create database `{db_name}`: {str(e)}"

def get_engine(config: dict = None):
    """Creates and returns a SQLAlchemy Engine for MySQL."""
    cfg = get_db_config(config)
    # Ensure database exists
    create_database_if_not_exists(cfg)
    
    user = cfg['user']
    password = cfg['password']
    host = cfg['host']
    port = cfg['port']
    database = cfg['database']
    
    connection_string = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
    return create_engine(connection_string, pool_recycle=3600, pool_pre_ping=True)

def test_connection(config: dict = None):
    """Tests MySQL server connection and database status."""
    cfg = get_db_config(config)
    try:
        ok, msg = create_database_if_not_exists(cfg)
        if not ok:
            return False, msg
        
        engine = get_engine(cfg)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT VERSION();")).fetchone()
            version = result[0] if result else "Unknown"
        return True, f"Successfully connected to MySQL {version} (Database: `{cfg['database']}`)"
    except Exception as e:
        return False, f"MySQL connection error: {str(e)}"

def init_mysql_db(config: dict = None):
    """Initializes tables in MySQL."""
    cfg = get_db_config(config)
    try:
        engine = get_engine(cfg)
        with engine.connect() as conn:
            # 1. Price Depth Summary Table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS price_depth_summary (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    trade_date DATE NOT NULL,
                    price DOUBLE NOT NULL,
                    buy_volume BIGINT DEFAULT 0,
                    sell_volume BIGINT DEFAULT 0,
                    other_volume BIGINT DEFAULT 0,
                    total_volume BIGINT DEFAULT 0,
                    trade_count INT DEFAULT 0,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_symbol_date_price (symbol, trade_date, price),
                    INDEX idx_symbol_date (symbol, trade_date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))
            
            # 2. Raw Intraday Trades Table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS intraday_trades (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    trade_id VARCHAR(50),
                    symbol VARCHAR(10) NOT NULL,
                    trade_time DATETIME NOT NULL,
                    trade_date DATE NOT NULL,
                    price DOUBLE NOT NULL,
                    volume BIGINT NOT NULL,
                    match_type VARCHAR(20),
                    INDEX idx_symbol_date (symbol, trade_date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))
            conn.commit()
        return True, "Tables `price_depth_summary` and `intraday_trades` initialized successfully."
    except Exception as e:
        return False, f"Error initializing MySQL tables: {str(e)}"

def save_price_depth_to_mysql(symbol: str, trade_date, price_depth_df: pd.DataFrame, raw_trades_df: pd.DataFrame = None, config: dict = None):
    """Saves aggregated price depth summary and raw intraday trades to MySQL."""
    if price_depth_df is None or price_depth_df.empty:
        return False, "Empty dataframe provided."
    
    cfg = get_db_config(config)
    init_mysql_db(cfg)
    engine = get_engine(cfg)
    
    symbol = symbol.upper()
    trade_date_str = str(trade_date)
    
    try:
        with engine.connect() as conn:
            # Delete existing session summary records to ensure clean replace/update
            conn.execute(
                text("DELETE FROM price_depth_summary WHERE symbol = :symbol AND trade_date = :trade_date"),
                {"symbol": symbol, "trade_date": trade_date_str}
            )
            conn.commit()
            
        # Prepare price depth dataframe for DB
        summary_to_save = price_depth_df.copy()
        summary_to_save['symbol'] = symbol
        summary_to_save['trade_date'] = trade_date_str
        
        # Ensure column mapping matches SQL schema
        col_map = {
            'buy_vol': 'buy_volume',
            'sell_vol': 'sell_volume',
            'other_vol': 'other_volume',
            'trade_count': 'trade_count',
            'total_volume': 'total_volume'
        }
        summary_to_save = summary_to_save.rename(columns=col_map)
        
        # Select required columns
        req_cols = ['symbol', 'trade_date', 'price', 'buy_volume', 'sell_volume', 'other_volume', 'total_volume', 'trade_count']
        for col in req_cols:
            if col not in summary_to_save.columns:
                summary_to_save[col] = 0
                
        summary_to_save = summary_to_save[req_cols]
        summary_to_save.to_sql('price_depth_summary', con=engine, if_exists='append', index=False)
        
        # Save raw trades if provided
        if raw_trades_df is not None and not raw_trades_df.empty:
            with engine.connect() as conn:
                conn.execute(
                    text("DELETE FROM intraday_trades WHERE symbol = :symbol AND trade_date = :trade_date"),
                    {"symbol": symbol, "trade_date": trade_date_str}
                )
                conn.commit()
                
            raw_to_save = raw_trades_df.copy()
            raw_to_save['symbol'] = symbol
            raw_to_save['trade_date'] = trade_date_str
            if 'time' in raw_to_save.columns:
                raw_to_save['trade_time'] = pd.to_datetime(raw_to_save['time'])
            if 'id' in raw_to_save.columns:
                raw_to_save['trade_id'] = raw_to_save['id'].astype(str)
                
            raw_cols = ['trade_id', 'symbol', 'trade_time', 'trade_date', 'price', 'volume', 'match_type']
            for col in raw_cols:
                if col not in raw_to_save.columns:
                    raw_to_save[col] = None
                    
            raw_to_save = raw_to_save[raw_cols]
            raw_to_save.to_sql('intraday_trades', con=engine, if_exists='append', index=False)
            
        return True, f"Saved {len(summary_to_save)} price depth levels for {symbol} on {trade_date_str}."
    except Exception as e:
        return False, f"Failed to save to MySQL: {str(e)}"

def get_price_depth_from_mysql(symbol: str, trade_date=None, config: dict = None) -> pd.DataFrame:
    """Fetches price depth summary from MySQL for a specific symbol and date."""
    cfg = get_db_config(config)
    try:
        engine = get_engine(cfg)
        symbol = symbol.upper()
        
        if trade_date:
            query = text("SELECT * FROM price_depth_summary WHERE symbol = :symbol AND trade_date = :trade_date ORDER BY price DESC")
            df = pd.read_sql(query, con=engine, params={"symbol": symbol, "trade_date": str(trade_date)})
        else:
            # Fetch latest date for symbol
            query_latest = text("SELECT MAX(trade_date) FROM price_depth_summary WHERE symbol = :symbol")
            with engine.connect() as conn:
                res = conn.execute(query_latest, {"symbol": symbol}).fetchone()
                latest_date = res[0] if res else None
                
            if latest_date:
                query = text("SELECT * FROM price_depth_summary WHERE symbol = :symbol AND trade_date = :trade_date ORDER BY price DESC")
                df = pd.read_sql(query, con=engine, params={"symbol": symbol, "trade_date": str(latest_date)})
            else:
                df = pd.DataFrame()
        return df
    except Exception as e:
        return pd.DataFrame()

def get_saved_sessions_from_mysql(config: dict = None) -> pd.DataFrame:
    """Returns a summary dataframe of all stock sessions stored in MySQL."""
    cfg = get_db_config(config)
    try:
        engine = get_engine(cfg)
        query = text("""
            SELECT 
                symbol AS Symbol,
                trade_date AS `Ngày Phân Tích`,
                COUNT(id) AS `Số Mức Giá`,
                SUM(total_volume) AS `Tổng Khối Lượng`,
                SUM(buy_volume) AS `KL Mua Chủ Động`,
                SUM(sell_volume) AS `KL Bán Chủ Động`,
                MAX(updated_at) AS `Thời Gian Lưu DB`
            FROM price_depth_summary
            GROUP BY symbol, trade_date
            ORDER BY trade_date DESC, symbol ASC
        """)
        df = pd.read_sql(query, con=engine)
        return df
    except Exception:
        return pd.DataFrame()

def delete_session_from_mysql(symbol: str, trade_date, config: dict = None):
    """Deletes stored session data for a ticker and date."""
    cfg = get_db_config(config)
    try:
        engine = get_engine(cfg)
        symbol = symbol.upper()
        trade_date_str = str(trade_date)
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM price_depth_summary WHERE symbol = :symbol AND trade_date = :trade_date"), {"symbol": symbol, "trade_date": trade_date_str})
            conn.execute(text("DELETE FROM intraday_trades WHERE symbol = :symbol AND trade_date = :trade_date"), {"symbol": symbol, "trade_date": trade_date_str})
            conn.commit()
        return True, f"Deleted {symbol} data on {trade_date_str}."
    except Exception as e:
        return False, f"Failed to delete session: {str(e)}"
