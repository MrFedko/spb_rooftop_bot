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
CREDENTIALS_FILE = "client_secret_650025962607-8f7juop8o1bp0j9l9ec7shjhu7991u53.apps.googleusercontent.com.json"
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
for num, road in enumerate(all_roads, 1):
    markup.add(types.InlineKeyboardButton(text=road[0], callback_data=f"road {num}"))  # делаем кнопки по первому столлбцу


@dp.message_handler(commands="start", state='*')
async def start_message(message: types.Message):
    await message.answer("""приветственное сообщение""", reply_markup=markup)



if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=False)
