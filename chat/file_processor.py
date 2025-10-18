import os
import mimetypes
import base64
from typing import Tuple, Dict, Any
from django.core.files.uploadedfile import UploadedFile
from PIL import Image
import PyPDF2
import io


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
            '.json': 'json',
            '.csv': 'csv',
            '.md': 'markdown',
            '.docx': 'document',
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
            elif file_type == 'json':
                return self._process_json_file(file)
            elif file_type == 'csv':
                return self._process_csv_file(file)
            elif file_type == 'markdown':
                return self._process_markdown_file(file)
            else:
                return file_type, 'Файл загружен, но содержимое не обработано'
        except Exception as e:
            return file_type, f'Ошибка при обработке файла: {str(e)}'
    
    def process_file_for_training(self, file: UploadedFile) -> Dict[str, Any]:
        """Обрабатывает файл для использования в обучении модели."""
        filename = file.name.lower()
        file_extension = os.path.splitext(filename)[1]
        
        if file_extension not in self.allowed_extensions:
            return {'error': 'Неподдерживаемый тип файла'}
        
        file_type = self.allowed_extensions[file_extension]
        
        try:
            if file_type == 'text':
                return self._process_text_for_training(file)
            elif file_type == 'python':
                return self._process_python_for_training(file)
            elif file_type == 'pdf':
                return self._process_pdf_for_training(file)
            elif file_type == 'image':
                return self._process_image_for_training(file)
            elif file_type == 'json':
                return self._process_json_for_training(file)
            elif file_type == 'csv':
                return self._process_csv_for_training(file)
            elif file_type == 'markdown':
                return self._process_markdown_for_training(file)
            else:
                return {'error': 'Тип файла не поддерживается для обучения'}
        except Exception as e:
            return {'error': f'Ошибка при обработке файла: {str(e)}'}
    
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
            file.seek(0)  # Сбрасываем позицию файла
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            
            for page_num in range(min(len(pdf_reader.pages), 5)):  # Ограничиваем первыми 5 страницами
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
            
            # Ограничиваем превью до 2000 символов
            preview = text[:2000] + '...' if len(text) > 2000 else text
            return 'pdf', preview if preview.strip() else f'PDF файл загружен (размер: {file.size} байт). Не удалось извлечь текст.'
        except Exception as e:
            return 'pdf', f'Ошибка при обработке PDF: {str(e)}'
    
    def _process_image_file(self, file: UploadedFile) -> Tuple[str, str]:
        """Обработка изображения."""
        try:
            file.seek(0)  # Сбрасываем позицию файла
            image = Image.open(file)
            
            # Получаем информацию об изображении
            info = f'Изображение: {image.format}, размер: {image.size}, режим: {image.mode}'
            
            # Конвертируем в base64 для передачи в API
            file.seek(0)
            image_data = file.read()
            base64_data = base64.b64encode(image_data).decode('utf-8')
            
            return 'image', f'{info}. Base64 данные готовы для передачи в API.'
        except Exception as e:
            return 'image', f'Ошибка при обработке изображения: {str(e)}'
    
    def _process_json_file(self, file: UploadedFile) -> Tuple[str, str]:
        """Обработка JSON файла."""
        try:
            file.seek(0)
            content = file.read().decode('utf-8')
            import json
            json_data = json.loads(content)
            
            # Ограничиваем превью
            preview = json.dumps(json_data, ensure_ascii=False, indent=2)[:2000]
            if len(json.dumps(json_data, ensure_ascii=False)) > 2000:
                preview += '...'
            
            return 'json', preview
        except Exception as e:
            return 'json', f'Ошибка при обработке JSON: {str(e)}'
    
    def _process_csv_file(self, file: UploadedFile) -> Tuple[str, str]:
        """Обработка CSV файла."""
        try:
            file.seek(0)
            content = file.read().decode('utf-8')
            
            # Ограничиваем превью до первых 20 строк
            lines = content.split('\n')[:20]
            preview = '\n'.join(lines)
            if len(content.split('\n')) > 20:
                preview += '\n...'
            
            return 'csv', preview
        except Exception as e:
            return 'csv', f'Ошибка при обработке CSV: {str(e)}'
    
    def _process_markdown_file(self, file: UploadedFile) -> Tuple[str, str]:
        """Обработка Markdown файла."""
        try:
            file.seek(0)
            content = file.read().decode('utf-8')
            
            # Ограничиваем превью до 2000 символов
            preview = content[:2000] + '...' if len(content) > 2000 else content
            return 'markdown', preview
        except Exception as e:
            return 'markdown', f'Ошибка при обработке Markdown: {str(e)}'
    
    # Методы для обработки файлов для обучения
    def _process_text_for_training(self, file: UploadedFile) -> Dict[str, Any]:
        """Обработка текстового файла для обучения."""
        try:
            file.seek(0)
            content = file.read().decode('utf-8')
            return {
                'type': 'text',
                'content': content,
                'size': len(content),
                'encoding': 'utf-8'
            }
        except Exception as e:
            return {'error': f'Ошибка при обработке текста: {str(e)}'}
    
    def _process_python_for_training(self, file: UploadedFile) -> Dict[str, Any]:
        """Обработка Python файла для обучения."""
        try:
            file.seek(0)
            content = file.read().decode('utf-8')
            return {
                'type': 'python',
                'content': content,
                'size': len(content),
                'language': 'python'
            }
        except Exception as e:
            return {'error': f'Ошибка при обработке Python: {str(e)}'}
    
    def _process_pdf_for_training(self, file: UploadedFile) -> Dict[str, Any]:
        """Обработка PDF файла для обучения."""
        try:
            file.seek(0)
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return {
                'type': 'pdf',
                'content': text,
                'size': len(text),
                'pages': len(pdf_reader.pages)
            }
        except Exception as e:
            return {'error': f'Ошибка при обработке PDF: {str(e)}'}
    
    def _process_image_for_training(self, file: UploadedFile) -> Dict[str, Any]:
        """Обработка изображения для обучения."""
        try:
            file.seek(0)
            image = Image.open(file)
            
            # Конвертируем в base64
            file.seek(0)
            image_data = file.read()
            base64_data = base64.b64encode(image_data).decode('utf-8')
            
            return {
                'type': 'image',
                'content': base64_data,
                'format': image.format,
                'size': image.size,
                'mode': image.mode,
                'mime_type': f'image/{image.format.lower()}' if image.format else 'image/jpeg'
            }
        except Exception as e:
            return {'error': f'Ошибка при обработке изображения: {str(e)}'}
    
    def _process_json_for_training(self, file: UploadedFile) -> Dict[str, Any]:
        """Обработка JSON файла для обучения."""
        try:
            file.seek(0)
            content = file.read().decode('utf-8')
            import json
            json_data = json.loads(content)
            
            return {
                'type': 'json',
                'content': json_data,
                'size': len(content),
                'structure': self._analyze_json_structure(json_data)
            }
        except Exception as e:
            return {'error': f'Ошибка при обработке JSON: {str(e)}'}
    
    def _process_csv_for_training(self, file: UploadedFile) -> Dict[str, Any]:
        """Обработка CSV файла для обучения."""
        try:
            file.seek(0)
            content = file.read().decode('utf-8')
            lines = content.split('\n')
            
            return {
                'type': 'csv',
                'content': content,
                'size': len(content),
                'rows': len(lines),
                'headers': lines[0].split(',') if lines else []
            }
        except Exception as e:
            return {'error': f'Ошибка при обработке CSV: {str(e)}'}
    
    def _process_markdown_for_training(self, file: UploadedFile) -> Dict[str, Any]:
        """Обработка Markdown файла для обучения."""
        try:
            file.seek(0)
            content = file.read().decode('utf-8')
            
            return {
                'type': 'markdown',
                'content': content,
                'size': len(content),
                'language': 'markdown'
            }
        except Exception as e:
            return {'error': f'Ошибка при обработке Markdown: {str(e)}'}
    
    def _analyze_json_structure(self, data: Any, path: str = "") -> Dict[str, Any]:
        """Анализирует структуру JSON для лучшего понимания данных."""
        if isinstance(data, dict):
            return {
                'type': 'object',
                'keys': list(data.keys()),
                'properties': {k: self._analyze_json_structure(v, f"{path}.{k}") for k, v in data.items()}
            }
        elif isinstance(data, list):
            if data:
                return {
                    'type': 'array',
                    'length': len(data),
                    'item_type': self._analyze_json_structure(data[0], f"{path}[0]")
                }
            else:
                return {'type': 'array', 'length': 0}
        else:
            return {'type': type(data).__name__, 'value': str(data)[:100]}
