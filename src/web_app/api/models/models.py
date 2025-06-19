from pydantic import BaseModel


class CypherQuery(BaseModel):
    query: str


class HttpRequest(BaseModel):
    location: str
    host: str


class FileContextQuery(BaseModel):
    file_path: str
    line_num: int


class ConstantQuery(BaseModel):
    var_name: str
    var_value: str = None
