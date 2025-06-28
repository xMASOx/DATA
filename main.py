import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
import aiosqlite
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

API_TOKEN = '7756358632:AAHslRehr2qgSVFNSVAwYEy4Hji0lewBgHc'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# таблица
async def init_db():
    async with aiosqlite.connect("database.db") as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                description TEXT,
                remind_time TEXT
            )
        ''')
        await db.commit()

# команда start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Привет! Я — твой ежедневник 📔.\nДобавь задачу с помощью команды:\n\n📌 /add MM-DD HH:MM Твоя задача>\nПример: /add 9-28 18:30 Позвонить бабушке")

@dp.message(Command("add"))
async def cmd_add(message: Message):
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            await message.answer("Используй формат: /add MM-DD HH:MM Твоя задача")
            return

        date_part = parts[1]
        time_part = parts[2].split()[0]
        task_text = " ".join(parts[2].split()[1:])

        now = datetime.now()
        remind_time = datetime.strptime(f"{now.year}-{date_part} {time_part}", "%Y-%m-%d %H:%M")

        if remind_time < now:
            remind_time = remind_time.replace(year=now.year + 1)

        async with aiosqlite.connect("database.db") as db:
            await db.execute(
                "INSERT INTO tasks (user_id, description, remind_time) VALUES (?, ?, ?)",
                (message.from_user.id, task_text, remind_time.isoformat())
            )
            await db.commit()

        await message.answer(f"Задача добавлена: {task_text} в {remind_time.strftime('%m-%d %H:%M')}")

    except Exception as e:
        await message.answer("Ошибка добавления задачи. Используй формат: /add MM-DD HH:MM задача")




@dp.message(Command("list"))
async def cmd_list(message: Message):
    async with aiosqlite.connect("database.db") as db:
        cursor = await db.execute(
            "SELECT description, remind_time FROM tasks WHERE user_id = ? ORDER BY remind_time",
            (message.from_user.id,)
        )
        tasks = await cursor.fetchall()
    if not tasks:
        await message.answer("У тебя нет запланированных задач.")
    else:
        response = "Твои задачи:\n"
        for desc, remind_time in tasks:
            dt = datetime.fromisoformat(remind_time)
            response += f"{dt.strftime('%m-%d %H:%M')} — {desc}\n"
        await message.answer(response)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("""
  Команды бота:
  /add MM-DD HH:MM задача
  /list — список задач
  /help — помощь
""")

# проверка задач
async def check_tasks():
    now = datetime.now().replace(second=0, microsecond=0)
    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT id, user_id, description FROM tasks WHERE remind_time = ?", (now.isoformat(),)) as cursor:
            async for task_id, user_id, desc in cursor:
                try:
                    await bot.send_message(user_id, f"⏰ Напоминание: {desc}")
                except:
                    pass
                await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        await db.commit()

# запуск
async def main():
    await init_db()
    scheduler.add_job(check_tasks, 'interval', minutes=1)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
