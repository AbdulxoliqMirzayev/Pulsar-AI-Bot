from __future__ import annotations

from aiogram import Bot


async def download_file_bytes(bot: Bot, file_id: str) -> bytes:
    file = await bot.get_file(file_id)
    buffer = await bot.download_file(file.file_path)
    return buffer.read()
