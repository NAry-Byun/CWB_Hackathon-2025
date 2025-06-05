import logging
import os
import sys
from datetime import datetime
from typing import Optional

def setup_azure_logger(name: str, level: str = None) -> logging.Logger:
    
    if level is None:
        level = os.getenv('LOG_LEVEL', 'INFO').upper()
    

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level, logging.INFO))
    
   
    if logger.handlers:
        return logger
    

    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level, logging.INFO))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    if not os.getenv('AZURE_FUNCTIONS_ENVIRONMENT'):
        try:
            
            log_dir = 'logs'
            os.makedirs(log_dir, exist_ok=True)
            
            
            log_filename = f"{log_dir}/ai_assistant_{datetime.now().strftime('%Y%m%d')}.log"
            
            file_handler = logging.FileHandler(log_filename, encoding='utf-8')
            file_handler.setLevel(getattr(logging, level, logging.INFO))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
        except Exception as e:
            
            logger.warning(f"파일 로깅 설정 실패: {e}")
    
    return logger

def log_function_call(func_name: str, args: dict = None, logger: logging.Logger = None):
    
    if logger is None:
        logger = logging.getLogger(__name__)
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.info(f"🔄 함수 호출: {func_name}")
            if args:
                logger.debug(f"   매개변수: {args}")
            
            try:
                result = func(*args, **kwargs)
                logger.info(f"✅ 함수 완료: {func_name}")
                return result
            except Exception as e:
                logger.error(f"❌ 함수 오류: {func_name} - {str(e)}")
                raise
        
        return wrapper
    return decorator

def log_performance(func_name: str, logger: logging.Logger = None):
    
    import time
    
    if logger is None:
        logger = logging.getLogger(__name__)
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            logger.info(f"⏱️ 성능 측정 시작: {func_name}")
            
            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                duration = end_time - start_time
                logger.info(f"📊 성능 측정 완료: {func_name} - {duration:.2f}초")
                return result
            except Exception as e:
                end_time = time.time()
                duration = end_time - start_time
                logger.error(f"❌ 성능 측정 오류: {func_name} - {duration:.2f}초 - {str(e)}")
                raise
        
        return wrapper
    return decorator