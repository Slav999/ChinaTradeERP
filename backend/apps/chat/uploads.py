from pathlib import Path
from zipfile import BadZipFile, ZipFile
from PIL import Image, UnidentifiedImageError
from rest_framework.exceptions import ValidationError


def validate_uploads(files):
    if len(files) > 5 or sum(f.size for f in files) > 50 * 1024 * 1024:
        raise ValidationError('Не более 5 файлов и 50 МБ в сообщении.')
    result = []
    for file in files:
        if not file.size or file.size > 20 * 1024 * 1024:
            raise ValidationError('Размер файла должен быть от 1 байта до 20 МБ.')
        name = Path(file.name.replace('\\', '/')).name[:255]
        ext = Path(name).suffix.lower()
        mime = None
        try:
            if ext in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
                with Image.open(file) as image:
                    if image.format not in ('JPEG', 'PNG', 'WEBP', 'GIF') or image.width * image.height > 40_000_000:
                        raise ValidationError('Недопустимое изображение или слишком большое разрешение.')
                    mime = Image.MIME[image.format]
                    image.verify()
            elif ext == '.pdf':
                if file.read(5) == b'%PDF-':
                    mime = 'application/pdf'
            elif ext in ('.docx', '.xlsx', '.pptx'):
                with ZipFile(file) as archive:
                    required = {'.docx': 'word/document.xml', '.xlsx': 'xl/workbook.xml', '.pptx': 'ppt/presentation.xml'}[ext]
                    if '[Content_Types].xml' in archive.namelist() and required in archive.namelist():
                        mime = 'application/octet-stream'
            elif ext in ('.doc', '.xls', '.ppt'):
                if file.read(8) == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
                    mime = 'application/octet-stream'
            elif ext in ('.txt', '.csv'):
                file.read().decode('utf-8-sig')
                mime = 'text/plain'
        except (UnidentifiedImageError, OSError, ValueError, BadZipFile, Image.DecompressionBombError):
            raise ValidationError('Файл повреждён или его содержимое не соответствует формату.')
        finally:
            file.seek(0)
        if mime is None:
            raise ValidationError('Поддерживаются фото JPG/PNG/WebP/GIF, PDF, Word, Excel, PowerPoint, TXT и CSV.')
        result.append((file, name, mime))
    return result
