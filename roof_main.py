import httplib2
from apiclient import discovery
from oauth2client.service_account import ServiceAccountCredentials
from info import roof_bot
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
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

all_roads = values['values']                                                        # all sheet on this place
markup = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
for num, road in enumerate(all_roads):
    markup.add(types.InlineKeyboardButton(text=road[0], callback_data=f"road {num}"))  # create buttons on first collumn


@dp.message_handler(commands="start", state='*')
async def start_message(message: types.Message):
    await message.answer("""приветственное сообщение""", reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data.startswith('start'), state='*')
async def start_message(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, """приветственное сообщение""", reply_markup=markup)
    await bot.delete_message(callback_query.from_user.id, callback_query.message.message_id)


@dp.callback_query_handler(lambda c: c.data.startswith('road'), state='*')  # catch handlers of excursions
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


@dp.callback_query_handler(lambda c: c.data.startswith('about'), state='*')  # ловим хэндлер экскурсии
async def show_full_info_road(callback_query: types.CallbackQuery, state: FSMContext):
    number_of_road = callback_query.data.split()[1]
    road = all_roads[int(number_of_road)]
    await bot.answer_callback_query(callback_query.id)
    all_buttons = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    all_buttons.add(types.InlineKeyboardButton(text="Назад", callback_data=f"road {number_of_road}"),
                    types.InlineKeyboardButton(text="Выбрать дату", callback_data=f"date_road {number_of_road}"))
    await bot.answer_callback_query(callback_query.id)
    await bot.send_photo(callback_query.from_user.id,
                         road[9],
                         road[2], parse_mode=types.ParseMode.MARKDOWN, reply_markup=all_buttons)
    await bot.delete_message(callback_query.from_user.id, callback_query.message.message_id)


@dp.callback_query_handler(lambda c: c.data.startswith('date_road'), state='*')  # ловим хэндлер даты
async def select_date_road(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data["number of road"] = callback_query.data.split()[1]
        data["count"] = 1
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, 'Выберите дату', reply_markup=await SimpleCalendar().start_calendar())
    await bot.delete_message(callback_query.from_user.id, callback_query.message.message_id)


@dp.callback_query_handler(simple_cal_callback.filter(), state='*')
async def process_simple_calendar(callback_query: types.CallbackQuery, callback_data, state: FSMContext):
    selected, date = await SimpleCalendar().process_selection(callback_query, callback_data)
    async with state.proxy() as data:
        count_people = data["count"]
    button = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button.add(types.InlineKeyboardButton(text="Группа", callback_data="group"),
               types.InlineKeyboardButton(text="Индивидуально", callback_data="individual"))
    button.add(types.InlineKeyboardButton(text="⬇ Количество человек ⬇", callback_data="_"))
    button.add(types.InlineKeyboardButton(text="➖", callback_data="-"),
               types.InlineKeyboardButton(text=count_people, callback_data="_"),
               types.InlineKeyboardButton(text="➕", callback_data="+"))
    await bot.answer_callback_query(callback_query.id)
    if selected:
        await callback_query.message.answer(f'''Вы выбрали *{date.strftime("%d/%m/%Y")}*
        
Далее выберите количество человек и формат посещения.
*Группа* - Вы пойдёте с такими же искателями нового и прекрасного.
*Индивидуально* - только Вы, Ваша компания и гид.''', parse_mode=types.ParseMode.MARKDOWN, reply_markup=button)
    async with state.proxy() as data:
        data['date'] = date.strftime("%d/%m/%Y")
    await bot.delete_message(callback_query.from_user.id, callback_query.message.message_id)


@dp.callback_query_handler(lambda call: call.data in ("-", "+"))        # change inline keyboard and select count of peoples
async def next_keyboard(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        if callback_query.data == "+":
            data["count"] += 1
        elif callback_query.data == "-":
            if data["count"] > 1:
                data["count"] -= 1
        count_people = data["count"]
    await bot.answer_callback_query(callback_query.id)
    button = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button.add(types.InlineKeyboardButton(text="Группа", callback_data="group"),
               types.InlineKeyboardButton(text="Индивидуально", callback_data="individual"))
    button.add(types.InlineKeyboardButton(text="⬇ Количество человек ⬇", callback_data="_"))
    button.add(types.InlineKeyboardButton(text="➖", callback_data="-"),
               types.InlineKeyboardButton(text=count_people, callback_data="_"),
               types.InlineKeyboardButton(text="➕", callback_data="+"))
    await callback_query.message.edit_reply_markup(button)


@dp.callback_query_handler(lambda c: c.data in ("group", "individual"), state='*')  # select time of road
async def select_date_road(callback_query: types.CallbackQuery, state: FSMContext):
    button_1 = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True) # 10 - 22
    button_2 = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True) # 10 - 18
    button_3 = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True) # 11 - 15
    array = [types.InlineKeyboardButton(text=f"{time}:00", callback_data=f"time {time}") for time in range(10, 23, 2)]
    button_1.add(*array)
    button_2.add(*array[0:5])
    array_2 = [types.InlineKeyboardButton(text=f"{time}:00", callback_data=f"time {time}") for time in range(11, 16, 2)]
    button_3.add(*array_2)
    current_buttons = None
    await bot.answer_callback_query(callback_query.id)
    async with state.proxy() as data:
        data["format"] = callback_query.data
        if data["number of road"] in ('3', '4'):
            if 2 <= int(data['date'].split('/')[1]) <= 9:
                current_buttons = button_2
            else:
                current_buttons = button_3
        elif data["number of road"] in ('0', '1', '2') and data['format'] == 'group':
            current_buttons = button_1
    if current_buttons:
        current_buttons.add(types.InlineKeyboardButton(text="К списку экскурсий", callback_data="start"))
        await callback_query.message.answer("Выберите время экскурсии", reply_markup=current_buttons)
    else:
        current_buttons = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        current_buttons.add(types.InlineKeyboardButton(text="Сверить заказ", callback_data=f"time any"))
        await callback_query.message.answer("Время проведения экскурсии необходимо согласовать с гидом.",
                                            reply_markup=current_buttons)
    await bot.delete_message(callback_query.from_user.id, callback_query.message.message_id)


@dp.callback_query_handler(lambda c: c.data.startswith("time"), state='*')  # finally
async def select_date_road(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    current_buttons = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    current_buttons.add(types.InlineKeyboardButton(text="Отправить заявку гиду", callback_data="ready"))
    current_buttons.add(types.InlineKeyboardButton(text="К началу", callback_data="start"))
    all_info = []
    async with state.proxy() as data:
        if callback_query.data.endswith('any'):
            data['time'] = 'время экскурсии необходимо обсудить'
        else:
            data['time'] = callback_query.data.split()[1] + ":00"
        for k, v in data.items():
            all_info.append(v)
    cost = 0
    if all_info[3] == "group":
        a = [790, 900, 790, 990, 790, 1000]
        cost = a[int(all_info[0])]
        all_info[3] = "в составе группы"
    else:
        if int(all_info[1]) == 1:
            b = [1500, 1500, 1300, 3500, 3000, 3000]
            cost = b[int(all_info[0])]
        else:
            c = [1500, 1500, 1300, 1800, 1500, 2000]
            cost = c[int(all_info[0])]
        all_info[3] = "индивидуальная экскурсия"

    total = (cost * all_info[1]) * 0.9
    if all_info[4].isnumeric():
        all_info[4] += ":00"
    else:
        all_info[4] = "время экскурсии необходимо обсудить с гидом"
    async with state.proxy() as data:
        data["cost"]  = cost
        data["total"] = total
        data["name"] = callback_query.from_user.username
    await callback_query.message.answer(f"""*Название экскурсии:* {all_roads[int(all_info[0])][1]}
*Количество человек:* {all_info[1]}
*Дата и время:* {all_info[2]}  {all_info[4]}
*Формат посещения:* {all_info[3]}
*Стоимость:* {cost} ✖ {all_info[1]} ➖ 10 % = {total}

""", reply_markup=current_buttons, parse_mode=types.ParseMode.MARKDOWN)
    await bot.delete_message(callback_query.from_user.id, callback_query.message.message_id)


@dp.callback_query_handler(lambda c: c.data.startswith("ready"), state='*')  # finally
async def select_date_road(callback_query: types.CallbackQuery, state: FSMContext):
    current_buttons = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    current_buttons.add(types.InlineKeyboardButton(text="Вернуться к списку экскурсий", callback_data="start"))
    async with state.proxy() as data:
        message = f"""Название экскурсии: {all_roads[int(data["number of road"])][1]}

Количество человек: {int(data["count"])}
Дата и время: {data["date"]}     {data["time"]}
Формат посещения: {data["format"]}
Стоимость: {int(data["cost"])} ✖ {int(data["count"])} ➖ 10 % = {int(data["total"])}
Telegram username: @{data["name"]}"""
    await bot.send_message("153194452", message, disable_notification=False)
    await callback_query.message.answer("Я передал всю информацию гиду. Он свяжется с Вами в ближайшее время",
                                        reply_markup=current_buttons)
    await bot.delete_message(callback_query.from_user.id, callback_query.message.message_id)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=False)
