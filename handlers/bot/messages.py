import asyncio

from aiogram import F
from aiogram.enums import ContentType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from keyboard.keyboard import create_group_participants_button, create_admin_panel_keyboard
from messages.translations_loader import translations
from system.dispatcher import router, bot, time_del
from system.sqlite import (fetch_user_data, reading_from_the_database_of_forbidden_words,
                           recording_actions_in_the_database)


@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext) -> None:
    await state.clear()  # Сбрасываем состояние FSM

    user_id = message.from_user.id
    keyboard = create_admin_panel_keyboard(user_id)

    await bot.send_message(
        message.chat.id,
        translations["ru"]["menu"]["user"],
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.message(Command("admin"))
async def admin_command(message: Message, state: FSMContext) -> None:
    await state.clear()  # Сбрасываем состояние FSM
    await bot.send_message(message.chat.id, translations["ru"]["menu"]["admin"],
                           reply_markup=create_group_participants_button(),
                           parse_mode="HTML")


@router.message(Command("help"))
async def help_command(message: Message, state: FSMContext) -> None:
    await state.clear()  # Сбрасываем состояние FSM
    await bot.send_message(message.chat.id, translations["ru"]["menu"]["help"],
                           reply_markup=create_group_participants_button(),
                           parse_mode="HTML")


@router.message(F.content_type == ContentType.TEXT)
async def handle_text_messages(message: Message) -> None:
    """
    Основной обработчик текстовых сообщений. Обрабатывает пересылаемые сообщения, упоминания, запрещенные слова и ссылки.

    :param message: Сообщение Telegram.
    """
    chat_id = message.chat.id
    user_id = message.from_user.id

    try:
        # Проверка на пересылку сообщений
        if message.forward_from or message.forward_from_chat:
            data_dict = fetch_user_data()
            if (chat_id, user_id) not in data_dict:
                await message.delete()
                warning = await message.answer(
                    f"<code>✅ {message.from_user.full_name}</code>\n"
                    f"<code>В чате запрещены пересылаемые сообщения.</code>",
                    parse_mode="HTML",
                )
                await asyncio.sleep(int(time_del))
                await warning.delete()
            return
        # Проверка на запрещенные слова
        for word in reading_from_the_database_of_forbidden_words():
            if word[0].lower() in message.text.lower():
                recording_actions_in_the_database(word[0], message)
                await message.delete()
                warning = await message.answer(
                    f"⚠ В вашем сообщении обнаружено запрещенное слово: <code>{word[0]}</code>. "
                    f"Пожалуйста, не используйте его в дальнейшем.",
                    parse_mode="HTML",
                )
                await asyncio.sleep(int(time_del))
                await warning.delete()
                return  # После удаления сообщения больше ничего не проверяем

        # Проверка на ссылки
        for entity in message.entities or []:
            if entity.type in ["url", "text_link", "mention"]:
                if (chat_id, user_id) not in fetch_user_data():
                    await message.delete()
                    warning = await message.answer(
                        f"<code>✅ {message.from_user.full_name}</code>\n"
                        f"<code>В чате запрещена публикация сообщений со ссылками.</code>",
                        parse_mode="HTML",
                    )
                    await asyncio.sleep(int(time_del))
                    await warning.delete()
                    return  # После удаления сообщения больше ничего не проверяем
    except Exception as e:
        logger.error(f"Ошибка при обработке текстового сообщения: {e}")


def register_message_handlers() -> None:
    """
    Регистрирует обработчики событий для бота.
    """
    router.message.register(handle_text_messages)
    router.message.register(start_command, Command("start"))
    router.message.register(admin_command, Command("admin"))
    router.message.register(help_command, Command("help"))
