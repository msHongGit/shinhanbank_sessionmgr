사용자 세션 로그: 

Log Format:timestamp, event_type, global_session_key, cusno(고객번호) session_state, error_message, error_code


fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d %(funcName)s() - %(message)s"
    )
Message(log payload):



class LoggerExtraData(BaseModel):
    logType: str = "-"
    custNo: str = "-"
    sessionId: str = "-"
    turnId: str = "-"
    agentId: str = "-"
    transactionId: str = "-"
    payload: object
SetupLog:



from app.****.logger_config import setup_es_logger
setup_es_logger()
Call Log:



    logger.eslog(
        LoggerExtraData(
            logType=logType,
            custNo=custNo,
            turnId=turnId,
            agentId=agent,
            transactionId=trxId,
            payload=logPayload
        )
    )
 
