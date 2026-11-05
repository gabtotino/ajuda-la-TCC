# services/upload_service.py
"""Upload seguro das imagens de tarefas.

Camadas de validação (todas no servidor, porque o navegador pode ser
contornado):
1. extensão permitida (jpg, jpeg, png, webp);
2. MIME type declarado pelo navegador compatível com a extensão;
3. assinatura real do arquivo ("magic bytes") — um .exe renomeado para
   .png é recusado aqui, mesmo com extensão e MIME corretos;
4. tamanho máximo por imagem (MAX_IMAGE_SIZE);
5. nome gerado pelo servidor (UUID) — o nome original do usuário nunca é
   usado no disco, o que elimina path traversal ("../../app.py") e
   colisões entre arquivos.
"""

import os
import uuid

from flask import current_app

ALLOWED_TYPES = {
    "jpg": ("image/jpeg",),
    "jpeg": ("image/jpeg",),
    "png": ("image/png",),
    "webp": ("image/webp",),
}


class UploadError(ValueError):
    """Imagem recusada; a mensagem é exibida ao usuário."""


def _detect_format(header):
    """Identifica o formato pelos primeiros bytes do arquivo."""
    if header.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    return None


def validate_image(file_storage):
    """Valida um arquivo enviado (werkzeug FileStorage) e devolve a extensão
    normalizada. Levanta UploadError com uma mensagem amigável."""
    original_name = file_storage.filename or ""
    extension = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
    if extension not in ALLOWED_TYPES:
        raise UploadError(f'"{original_name}": use imagens JPG, PNG ou WEBP.')

    if file_storage.mimetype not in ALLOWED_TYPES[extension]:
        raise UploadError(f'"{original_name}": o tipo do arquivo não corresponde a uma imagem.')

    stream = file_storage.stream
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(0)
    if size == 0:
        raise UploadError(f'"{original_name}": o arquivo está vazio.')
    if size > current_app.config["MAX_IMAGE_SIZE"]:
        limit_mb = current_app.config["MAX_IMAGE_SIZE"] // (1024 * 1024)
        raise UploadError(f'"{original_name}": cada imagem pode ter no máximo {limit_mb} MB.')

    detected = _detect_format(stream.read(16))
    stream.seek(0)
    expected = "jpeg" if extension in ("jpg", "jpeg") else extension
    if detected != expected:
        raise UploadError(f'"{original_name}": o conteúdo não é uma imagem {extension.upper()} válida.')

    return "jpg" if extension == "jpeg" else extension


def save_image(file_storage, extension):
    """Grava o arquivo com nome aleatório e devolve esse nome."""
    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.{extension}"
    file_storage.save(os.path.join(folder, filename))
    return filename


def delete_image_file(filename):
    """Remove o arquivo do disco, se existir. basename() garante que um nome
    adulterado no banco nunca aponte para fora da pasta de uploads."""
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], os.path.basename(filename))
    if os.path.isfile(path):
        os.remove(path)


def selected_files(files, field_name="images"):
    """Arquivos realmente escolhidos no <input type="file" multiple>.

    Sem seleção, o navegador ainda envia um item vazio; ele é ignorado.
    """
    return [f for f in files.getlist(field_name) if f and f.filename]
