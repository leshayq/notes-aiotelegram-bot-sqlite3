from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.dispatcher import FSMContext, filters

from sqlite import db_start, create_user, create_tag, count_tag, show_tags, show_notes, add_content, check_tag, delete_tag, find_tag_id

from token_api import TOKEN_API
async def on_startup(_):
    await db_start()

storage = MemoryStorage()

TOKEN_API = TOKEN_API
bot = Bot(TOKEN_API)
dp = Dispatcher(bot, storage=storage)

# Классы для создания состояний FSM

class AddTagStates(StatesGroup):
    name = State()

class Notes(StatesGroup):
    number = State()

class AddNotes(StatesGroup):
    tag_id = State()
    content = State()

class DeleteTags(StatesGroup):
    tag_id = State()

#Клавиатура приветствия
def get_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Добавить тэг')).add(KeyboardButton('Мои тэги')).insert(KeyboardButton('Удалить тэг'))
    return kb

#Клавиатура по кнопке "Мои тэги"
def tags_kb():
    tkb = ReplyKeyboardMarkup(resize_keyboard=True)
    tkb.add(KeyboardButton('Записи')).add(KeyboardButton('Добавить запись')).add(KeyboardButton('Назад'))
    return tkb

#Клавиатура отмены действия
def cancel_kb():
    ckb = ReplyKeyboardMarkup(resize_keyboard=True)
    ckb.add(KeyboardButton('Назад'))
    return ckb

#Подтвердить валидность имени тэга
def verify_valid(text):
    if (len(text) < 1 or len(text) > 30) or text.startswith('/'):
        return False
    return True

#Команда старт/приветствие
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer('Добро пожаловать! <b>Это бот-заметки.</b> Начнем?', reply_markup=get_kb(), parse_mode='html')
    await create_user(user_id=message.from_user.id, chat_id=message.chat.id)

#Назад, главное меню
@dp.message_handler(filters.Text(equals='Назад'))
async def cmd_cancel(message: types.Message):
    await message.delete()
    await message.answer('Вы отменили действие.', reply_markup=get_kb())

#Добавить тэг
@dp.message_handler(filters.Text(equals='Добавить тэг'))
async def cmd_add_tag(message: types.Message):
    await message.answer('Хорошо! Теперь отправь название для тэга. \n', reply_markup=cancel_kb())
    await AddTagStates.name.set()

@dp.message_handler(state=AddTagStates.name)
async def state_tag_name(message: types.Message, state: FSMContext):
    if verify_valid(message.text):
        async with state.proxy() as data:
            data['name'] = message.text
        if message.text != 'Назад':
            await message.reply('Тэг был успешно добавлен.', reply_markup=get_kb())
            await create_tag(message.text, message.chat.id)
            await state.finish()
        else:
            await state.finish()
            await cmd_cancel(message)
    else:
        await message.answer('Неверный формат тэга. Тэг должен содержать не более 30 и не менее 1 символа, а также не начинаться со знака <b>/</b>. \nПопробуйте еще раз.', parse_mode='html', reply_markup=cancel_kb())

#Функция, которая собирает и формирует список тэгов
async def message_tags(message: types.Message):
    message_tags = ''
    tags = await show_tags(message.from_user.id)
    if await count_tag(user_id=message.from_user.id):
        for i in range(1, len(await show_tags(message.from_user.id)) + 1):
            result = await find_tag_id(tags[i - 1])
            if result:  # Check if result is not None
                message_tags += f'{i}. {tags[i - 1]}  \n'
            else:
                message_tags += f'{tags[i - 1]}  \n'  # Handle the case where result is None
        return message_tags
    return None


@dp.message_handler(filters.Text(equals='Мои тэги'))
async def cmd_my_tags(message: types.Message):
    if await message_tags(message):
        await message.answer(f'Вот список твоих тэгов: ({await count_tag(user_id=message.from_user.id)}) \n{await message_tags(message)}', reply_markup=tags_kb())
    else:
        await message.answer('Упс! Ты еще не добавил ни одного тэга. Исправим?', reply_markup=get_kb())

#Добавление записи

@dp.message_handler(filters.Text(equals='Добавить запись'))
async def cmd_add_note(message: types.Message):
    if await message_tags(message):
        await message.answer(f'Хорошо, выбери тэг для добавления записи.\n{await message_tags(message)}')
        await AddNotes.tag_id.set()
    else:
        await message.answer('Упс! Ты еще не добавил ни одного тэга. Исправим?', reply_markup=get_kb())

@dp.message_handler(lambda message: message.text.isdigit(), state=AddNotes.tag_id)
async def add_note_digit(message: types.Message, state: FSMContext):
    tag_number = message.text
    if await check_tag(tag_number, message.from_user.id):
        await state.update_data(tag_number=tag_number)
        await message.answer('Хорошо, теперь отправь мне текст для записи.')
        await AddNotes.next()
    else:
        await message.answer('Тэга с таким порядковым номером не существует. Попробуйте другой.')

@dp.message_handler(lambda message: not message.text.isdigit(), state=AddNotes.tag_id)
async def add_note_wrong_format(message: types.Message, state: FSMContext):
    if message.text != 'Назад':
        await message.answer('Неверный ввод данных. Тэг должен быть числом')
    else:
        await state.finish()
        await cmd_cancel(message)


@dp.message_handler(state=AddNotes.content)
async def add_note_content(message: types.Message, state: FSMContext):
    data = await state.get_data()
    tag_number = data.get('tag_number')
    if tag_number:
        await add_content(tag_number, message.from_user.id, message.text)
        await state.finish()
        await message.reply('Запись была успешно добавлена!', reply_markup=get_kb())

#Отобразить записи

@dp.message_handler(filters.Text(equals='Записи'))
async def cmd_show_notes(message: types.Message):
    await message.answer(f'Хорошо! Выбери по какому тэгу отобразить записи. Отправь число без точки в конце.\n{await message_tags(message)}', reply_markup=cancel_kb())
    await Notes.number.set()


@dp.message_handler(lambda message: message.text.isdigit(), state=Notes.number)
async def show_notes_by_tag(message: types.Message, state: FSMContext):
    if await show_notes(message.text):
        for i in await show_notes(message.text):
            await message.answer(i[3], reply_markup=get_kb())
        await state.finish()
    else:
        await message.answer('По заданному тэгу нет записей.', reply_markup=cancel_kb())

@dp.message_handler(lambda message: not message.text.isdigit(), state=Notes.number)
async def show_notes_wrong_format(message: types.Message, state: FSMContext):
    if message.text != 'Назад':
        await message.answer('Вы неверно ввели данные. Введите цифру.', reply_markup=cancel_kb())
    else:
        await state.finish()
        await cmd_cancel(message)

#Удаление тэга

@dp.message_handler(filters.Text(equals='Удалить тэг'))
async def cmd_delete_tag(message: types.Message):
    if await message_tags(message):
        await message.answer(f'Хорошо! Выбери какой номер тэга ты хочешь удалить...\n{await message_tags(message)}', reply_markup=cancel_kb())
        await DeleteTags.tag_id.set()
    else:
        await message.answer('Упс! Ты еще не добавил ни одного тэга. Исправим?', reply_markup=get_kb())
        
@dp.message_handler(lambda message: message.text.isdigit(), state=DeleteTags.tag_id)
async def delete_tag_num(message: types.Message, state: FSMContext):
    if await check_tag(message.text, message.from_user.id):
        await delete_tag(message.from_user.id, message.text)
        await message.reply('Тэг был успешно удален.', reply_markup=get_kb())
        await state.finish()
    else:
        await message.answer('Тэга с таким порядковым номером не существует. Попробуйте другой.', reply_markup=cancel_kb())

@dp.message_handler(lambda message: not message.text.isdigit(), state=DeleteTags.tag_id)
async def delete_tag_wrong_format(message: types.Message, state: FSMContext):
    if message.text != 'Назад':
        await message.answer('Вы неверно ввели данные. Введите цифру.', reply_markup=cancel_kb())
    else:
        await state.finish()
        await cmd_cancel(message)

#Запуск бота
if __name__ == "__main__":
    executor.start_polling(dp,
                           skip_updates=True,
                           on_startup=on_startup
                           )