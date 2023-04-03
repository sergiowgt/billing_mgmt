from typing import Any, Optional
from abc import ABC, abstractmethod

class IGoogleDriveHandler(ABC):

    @abstractmethod
    def get_excel_file(self, file_id: str) -> bytes:
        ...

    @abstractmethod
    def get_google_sheets_file(self, file_id: str) -> bytes:
        ...

    @abstractmethod
    def upload_file(self, local_file_name: str,  file_name: str, parent_id: str='') -> Any:
        ...

    @abstractmethod
    def find_file(self, name: str, parent_id: str = '') -> Optional[Any]:
        ...

    @abstractmethod
    def create_folder(self, name, parent_id: str = '') -> Any:
        ...
