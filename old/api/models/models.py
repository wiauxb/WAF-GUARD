from typing import Optional
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


class ConfigContent(BaseModel):
    filename: str
    is_folder: bool
    file_content: Optional[str] = None

class FileContent(BaseModel):
    path: str
    content: str
