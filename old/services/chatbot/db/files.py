from db.connection import get_files_pool

class ConfigFileIterator:
    def __init__(self, content: str, filepath: str):
        self.filepath = filepath
        self.lines = content.splitlines(keepends=True)
        self._index = 0
    def __iter__(self):
        return self
    def __next__(self):
        if self._index < len(self.lines):
            line = self.lines[self._index]
            self._index += 1
            return line
        else:
            raise StopIteration
    def read(self):
        return ''.join(self.lines)
    def readline(self):
        if self._index < len(self.lines):
            line = self.lines[self._index]
            self._index += 1
            return line
        else:
            return ''

def get_current_config_file(filepath: str):
    """
    Fetches a specific file from the current configuration loaded in the database.
    
    Args:
        filepath (str): The path to the configuration file.
        
    Returns:
        ConfigFileIterator: An object to iterate over the lines of the configuration file.
    """
    pool = get_files_pool()
    with pool.connection() as conn:
        cursor = conn.cursor()
        # Get the current config_id from selected_config
        cursor.execute("SELECT config_id FROM selected_config LIMIT 1")
        row = cursor.fetchone()
        if not row:
            raise FileNotFoundError("No selected configuration found.")
        config_id = row[0]
        # Get the file content from files table
        cursor.execute(
            "SELECT content FROM files WHERE path = %s AND config_id = %s",
            (filepath, config_id)
        )
        file_content = cursor.fetchone()
        if file_content:
            # file_content[0] is bytea, decode to str
            content_str = file_content[0].decode('utf-8')
            return ConfigFileIterator(content_str, filepath)
        else:
            raise FileNotFoundError(f"File not found for path: {filepath} and config_id: {config_id}")
        
    