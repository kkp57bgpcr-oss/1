import os
import sqlite3
import asyncio
import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError

# ============ 1. 基础配置 ============
API_ID = 2040 
API_HASH = "b18441a1ff607e10a989891a5462e627"
BOT_TOKEN = "7881731610:AAGZ4jIlDqCn8pLT1ubdlpWdtRNJsg3Qe00"
ADMIN_ID = 6649617045  # 你的ID,默认最高权限

# ✨ 设备伪装配置
DEVICE_CONFIG = {
    'device_model': "iPhone 12",
    'system_version': "26.3",
    'app_version': "12.3",
    'lang_code': "zh-Hans-CN",
    'system_lang_code': "zh-Hans"
}

SESSION_DIR = "sessions"
if not os.path.exists(SESSION_DIR): os.makedirs(SESSION_DIR)

# 登录状态机
login_process = {}

# ============ 2. 数据库与权限逻辑 ============
def init_db():
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS authorized_users (id INTEGER PRIMARY KEY)')
    cursor.execute('CREATE TABLE IF NOT EXISTS accounts (phone TEXT PRIMARY KEY, user_id INTEGER)')
    cursor.execute('CREATE TABLE IF NOT EXISTS bots (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, command TEXT, user_id INTEGER)')
    conn.commit()
    conn.close()

init_db()

def is_user_allowed(uid):
    if uid == ADMIN_ID: return True
    conn = sqlite3.connect('data.db')
    res = conn.execute('SELECT 1 FROM authorized_users WHERE id = ?', (uid,)).fetchone()
    conn.close()
    return res is not None

# ============ 3. 核心执行逻辑 (定时与间隔) ============

async def run_all_tasks(trigger_type="自动"):
    """核心签到逻辑:遍历账号 -> 遍历机器人 -> 间隔6秒"""
    conn = sqlite3.connect('data.db')
    accounts = conn.execute('SELECT phone FROM accounts').fetchall()
    bots = conn.execute('SELECT username, command FROM bots').fetchall()
    conn.close()
    
    if not accounts or not bots:
        return

    print(f"[{datetime.datetime.now()}] 启动{trigger_type}全量签到任务...")
    
    for acc in accounts:
        phone = acc[0]
        client = TelegramClient(os.path.join(SESSION_DIR, phone), API_ID, API_HASH, **DEVICE_CONFIG)
        try:
            await client.connect()
            if await client.is_user_authorized():
                for b_user, b_cmd in bots:
                    await client.send_message(b_user, b_cmd)
                    # ✨ 签到完一个机器人自动等六秒再签到下一个
                    await asyncio.sleep(6) 
            await client.disconnect()
        except Exception as e:
            print(f"账号 {phone} 执行出错: {e}")

    # 任务完成后通知管理员
    await bot.send_message(ADMIN_ID, f"⏰ **{trigger_type}签到任务已完成**\n频率: 6秒/机器人\n设备: {DEVICE_CONFIG['device_model']}")

async def custom_scheduler():
    """✨ 零依赖定时器: 替代 apscheduler"""
    print("⏰ 内部定时器已启动,监控时间点:00:05 & 12:05")
    while True:
        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M")
        
        # 匹配 00:05 或 12:05 (24:05)
        if current_time in ["00:05", "12:05"]:
            # 使用 create_task 异步运行,不阻塞定时器继续倒计时
            asyncio.create_task(run_all_tasks("自动定时"))
            # 等过这一分钟,防止重复触发
            await asyncio.sleep(61)
        
        # 每30秒检查一次,既精准又省电
        await asyncio.sleep(30)

# ============ 4. 机器人实例与 UI ============
bot = TelegramClient('manager_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

async def send_main_menu(event):
    text = "🔧 **Telegram 机器人管理器**\n\n请选择操作:"
    buttons = [
        [Button.inline("📱 账号管理", b"menu_account")],
        [Button.inline("🤖 签到机器人管理", b"menu_bot")],
        [Button.inline("🚀 发送指令", b"menu_send")],
        [Button.inline("📊 查看状态", b"menu_status")]
    ]
    if isinstance(event, events.CallbackQuery.Event): await event.edit(text, buttons=buttons)
    else: await event.reply(text, buttons=buttons)

async def send_account_menu(event):
    text = "📱 **账号管理**\n\n请选择操作:"
    buttons = [
        [Button.inline("➕ 添加账号 (交互登录)", b"acc_add_phone")],
        [Button.inline("📩 导入 Session 文件", b"acc_import_session")],
        [Button.inline("👁️ 查看账号", b"acc_view")],
        [Button.inline("⬅️ 返回主菜单", b"main_menu")]
    ]
    await event.edit(text, buttons=buttons)

async def send_bot_menu(event):
    text = "🤖 **签到机器人管理**\n\n请选择操作:"
    buttons = [
        [Button.inline("➕ 添加 bot", b"bot_add")],
        [Button.inline("❌ 删除 bot", b"bot_del")],
        [Button.inline("👁️ 查看 bot", b"bot_view")],
        [Button.inline("🔄 编辑 bot 关联", b"bot_edit")],
        [Button.inline("⬅️ 返回主菜单", b"main_menu")]
    ]
    await event.edit(text, buttons=buttons)

async def send_cmd_menu(event):
    text = "🚀 **发送指令**\n\n请选择发送方式:"
    buttons = [
        [Button.inline("🚀 立即发送指令", b"send_now")],
        [Button.inline("⚡ 发送所有账号", b"send_all_acc")],
        [Button.inline("⬅️ 返回主菜单", b"main_menu")]
    ]
    await event.edit(text, buttons=buttons)

# ============ 5. 回调逻辑与权限锁 ============

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    uid = event.sender_id
    if not is_user_allowed(uid):
        await event.answer("⚠️ 当前账号为普通用户,无法使用该功能。", alert=True)
        return

    data = event.data
    if data == b"main_menu": await send_main_menu(event)
    elif data == b"menu_account": await send_account_menu(event)
    elif data == b"menu_bot": await send_bot_menu(event)
    elif data == b"menu_send": await send_cmd_menu(event)
    elif data == b"menu_status":
        conn = sqlite3.connect('data.db')
        a_c = conn.execute('SELECT COUNT(*) FROM accounts').fetchone()[0]
        b_c = conn.execute('SELECT COUNT(*) FROM bots').fetchone()[0]
        conn.close()
        await event.edit(f"📊 **发送状态**\n\n已接入: {a_c} | 监控中: {b_c}", buttons=[Button.inline("⬅️ 返回", b"main_menu")])
    elif data == b"acc_add_phone":
        await event.edit("📱 请输入手机号 (带+86)")
        login_process[uid] = {'step': 'get_phone'}
    elif data == b"send_all_acc":
        await event.answer("🚀 正在手动启动全量签到...", alert=False)
        asyncio.create_task(run_all_tasks(trigger_type="手动"))

# ============ 6. 录入与授权指令 ============

@bot.on(events.NewMessage)
async def handle_input(event):
    uid = event.sender_id
    text = event.raw_text.strip()

    if text.startswith('/auth') and uid == ADMIN_ID:
        try:
            target = int(text.split()[1])
            conn = sqlite3.connect('data.db')
            conn.execute('INSERT OR REPLACE INTO authorized_users VALUES (?)', (target,))
            conn.commit(); conn.close()
            await event.reply(f"✅ 已授权用户 `{target}`")
        except: pass
        return

    if not is_user_allowed(uid):
        if text.startswith('/start'): await event.reply("🚫 权限拦截:请联系管理员。")
        return

    if uid in login_process:
        state = login_process[uid]
        if state['step'] == 'get_phone':
            c = TelegramClient(os.path.join(SESSION_DIR, text), API_ID, API_HASH, **DEVICE_CONFIG)
            await c.connect()
            try:
                res = await c.send_code_request(text)
                login_process[uid] = {'c': c, 'p': text, 'hash': res.phone_code_hash, 'step': 'get_code'}
                await event.reply("📩 验证码已发送,请输入:")
            except Exception as e:
                await event.reply(f"❌ 错误: {e}"); login_process.pop(uid)
        elif state['step'] == 'get_code':
            try:
                await state['c'].sign_in(state['p'], text, phone_code_hash=state['hash'])
                conn = sqlite3.connect('data.db'); conn.execute('INSERT OR REPLACE INTO accounts VALUES (?, ?)', (state['p'], uid)); conn.commit(); conn.close()
                await state['c'].disconnect(); login_process.pop(uid)
                await event.reply(f"🎊 账号 {state['p']} 已托管成功!")
            except SessionPasswordNeededError:
                state['step'] = 'get_pwd'; await event.reply("🔐 请输入二级密码:")
            except: await event.reply("❌ 验证码错误"); login_process.pop(uid)
        elif state['step'] == 'get_pwd':
            try:
                await state['c'].sign_in(password=text)
                conn = sqlite3.connect('data.db'); conn.execute('INSERT OR REPLACE INTO accounts VALUES (?, ?)', (state['p'], uid)); conn.commit(); conn.close()
                await state['c'].disconnect(); login_process.pop(uid)
                await event.reply("🎊 二级验证成功!")
            except: await event.reply("❌ 密码错误")
        return

    if '@' in text and not text.startswith('/'):
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            conn = sqlite3.connect('data.db'); conn.execute('INSERT INTO bots (username, command, user_id) VALUES (?, ?, ?)', (parts[0], parts[1], uid)); conn.commit(); conn.close()
            await event.reply("✅ 签到机器人任务已添加。")

# ============ 7. 启动程序 ============

@bot.on(events.NewMessage(pattern='/start'))
async def on_start(e):
    if is_user_allowed(e.sender_id): await send_main_menu(e)

print(f"📱 模拟设备: iPhone 12 (iOS 26.3)")
print("✅ 定时任务: 00:05 & 12:05 (零依赖模式)")
print("✅ 执行频率: 机器人间隔 6 秒")
print("💎 机器人运行中...")

# ✨ 启动自定义定时循环
bot.loop.create_task(custom_scheduler())
bot.run_until_disconnected()
