import os
import mimetypes
from typing import Tuple
from django.core.files.uploadedfile import UploadedFile


class FileProcessor:
    """Класс для обработки загруженных файлов."""
    
    def __init__(self):
        self.allowed_extensions = {
            '.txt': 'text',
            '.py': 'python',
            '.pdf': 'pdf',
            '.jpg': 'image',
            '.jpeg': 'image',
            '.png': 'image',
            '.gif': 'image',
        }
    
    def process_file(self, file: UploadedFile) -> Tuple[str, str]:
        """Обрабатывает загруженный файл и возвращает тип и превью содержимого."""
        filename = file.name.lower()
        file_extension = os.path.splitext(filename)[1]
        
        if file_extension not in self.allowed_extensions:
            return 'unknown', 'Неподдерживаемый тип файла'
        
        file_type = self.allowed_extensions[file_extension]
        
        try:
            if file_type == 'text':
                return self._process_text_file(file)
            elif file_type == 'python':
                return self._process_python_file(file)
            elif file_type == 'pdf':
                return self._process_pdf_file(file)
            elif file_type == 'image':
                return self._process_image_file(file)
            else:
                return file_type, 'Файл загружен, но содержимое не обработано'
        except Exception as e:
            return file_type, f'Ошибка при обработке файла: {str(e)}'
    
    def _process_text_file(self, file: UploadedFile) -> Tuple[str, str]:
        """Обработка текстового файла."""
        try:
            content = file.read().decode('utf-8')
            # Ограничиваем превью до 2000 символов
            preview = content[:2000] + '...' if len(content) > 2000 else content
            return 'text', preview
        except UnicodeDecodeError:
            return 'text', 'Ошибка декодирования текстового файла'
    
    def _process_python_file(self, file: UploadedFile) -> Tuple[str, str]:
        """Обработка Python файла."""
        try:
            content = file.read().decode('utf-8')
            # Ограничиваем превью до 2000 символов
            preview = content[:2000] + '...' if len(content) > 2000 else content
            return 'python', preview
        except UnicodeDecodeError:
            return 'python', 'Ошибка декодирования Python файла'
    
    def _process_pdf_file(self, file: UploadedFile) -> Tuple[str, str]:
        """Обработка PDF файла."""
        try:
            # Пока просто возвращаем информацию о файле
            # В будущем здесь можно добавить PyPDF2 или pdfplumber
            return 'pdf', f'PDF файл загружен (размер: {file.size} байт). Обработка PDF пока не реализована.'
        except Exception as e:
            return 'pdf', f'Ошибка при обработке PDF: {str(e)}'
    
    def _process_image_file(self, file: UploadedFile) -> Tuple[str, str]:
        """Обработка изображения."""
        try:
            # Пока просто возвращаем информацию о файле
            # В будущем здесь можно добавить OCR с помощью pytesseract
            return 'image', f'Изображение загружено (размер: {file.size} байт). OCR пока не реализован.'
        except Exception as e:
            return 'image', f'Ошибка при обработке изображения: {str(e)}'
