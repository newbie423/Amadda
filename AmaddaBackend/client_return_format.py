from typing import Any

class ClientReturnFormat:
    @staticmethod
    def __GetClientReturnFormat(execute_state:str, message:str, value:dict[str, Any]={}):
        return {
            "execute_state":execute_state,
            "message":message,
            "value":value
        }

    @staticmethod
    def Success(message:str="", value:dict[str, Any]={}):
        return ClientReturnFormat.__GetClientReturnFormat("success", message, value)

    @staticmethod
    def Warning(message:str="", value:dict[str, Any]={}):
        return ClientReturnFormat.__GetClientReturnFormat("warning", message, value)

    @staticmethod
    def Error(message:str="", value:dict[str, Any]={}):
        return ClientReturnFormat.__GetClientReturnFormat("error", message, value)

