import httplib2
from apiclient import discovery
from oauth2client.service_account import ServiceAccountCredentials
from info import roof_bot
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram_calendar import simple_cal_callback, SimpleCalendar
import sqlite3


# add our bot and memory storage
token_bot = roof_bot.token
bot = Bot(token_bot)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
logging.basicConfig(level=logging.INFO)


# add google sheets
CREDENTIALS_FILE = "googlesheets.json"
credentials = ServiceAccountCredentials.from_json_keyfile_name(
            CREDENTIALS_FILE,
            ['https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'])
httpAuth = credentials.authorize(httplib2.Http())
service = discovery.build('sheets', 'v4', http=httpAuth)
values = service.spreadsheets().values().get(
            spreadsheetId=roof_bot.spreadsheet_id,
            range='A2:K10',
            majorDimension='ROWS'
            ).execute()

all_roads = values['values']                                                        # вся таблица теперь здесь
markup = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
for num, road in enumerate(all_roads):
    markup.add(types.InlineKeyboardButton(text=road[0], callback_data=f"road {num}"))  # делаем кнопки по первому столбцу


@dp.message_handler(commands="start", state='*')
async def start_message(message: types.Message):
    await message.answer("""приветственное сообщение""", reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data.startswith('start'), state='*')
async def start_message(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, """приветственное сообщение""", reply_markup=markup)
    await bot.delete_message(callback_query.from_user.id, callback_query.message.message_id)


@dp.callback_query_handler(lambda c: c.data.startswith('road'), state='*')  # ловим хэндлер экскурсии
async def show_about_road(callback_query: types.CallbackQuery, state: FSMContext):
    number_of_road = callback_query.data.split()[1]
    road = all_roads[int(number_of_road)]
    all_buttons = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    all_buttons.add(types.InlineKeyboardButton(text="Назад", callback_data="start"),
                    types.InlineKeyboardButton(text="Выбрать дату", callback_data=f"date_road {number_of_road}"))
    all_buttons.add(types.InlineKeyboardButton(text="Полное описание", callback_data=f"about {number_of_road}"))
    await bot.answer_callback_query(callback_query.id)
    await bot.send_photo(callback_query.from_user.id,
                         road[10],
                         f"""*{road[1]}*
                         
{road[8]}

*Длительность:* {road[3]}
*Стоимость:*
> в составе группы {road[4]}
> индивидуальная экскурсия {road[6]}
""", parse_mode=types.ParseMode.MARKDOWN, reply_markup=all_buttons)
    await bot.delete_message(callback_query.from_user.id, callback_query.message.message_id)


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=False)
