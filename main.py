import os
import sqlite3
import asyncio
import datetime
import sys
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError

# ============ 1. 基础配置 ============
API_ID = 2040 
API_HASH = "b18441a1ff607e10a989891a5462e627"
BOT_TOKEN = "8505048236:AAFHPC3448Gti60whSAC9mak_oKzd7BN1eY"
ADMIN_ID = 6649617045  # 你的ID,默认最高权限

# ✨ 设备伪装配置 (iPhone 12 + Swiftgram 12.3)
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
        # 使用伪装配置实例化客户端
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
    try:
        await bot.send_message(ADMIN_ID, f"⏰ **{trigger_type}签到任务已完成**\n频率: 6秒/机器人\n设备: {DEVICE_CONFIG['device_model']}")
    except:
        pass

async def custom_scheduler():
    """✨ 零依赖定时器: 替代定时库"""
    print("⏰ 内部定时器已启动, 监控时间点: 00:05 & 12:05")
    while True:
        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M")
        
        # 匹配定时时间
        if current_time in ["00:05", "12:05"]:
            asyncio.create_task(run_all_tasks("自动定时"))
            await asyncio.sleep(61) # 避开重复触发
        
        await asyncio.sleep(30) # 每30秒检查一次

# ============ 4. UI 界面定义 ============

async def send_main_menu(event_or_client, chat_id=None):
    """主菜单"""
    text = "🔧 **Telegram 机器人管理器**\n\n请选择操作:"
    buttons = [
        [Button.inline("📱 账号管理", b"menu_account")],
        [Button.inline("🤖 签到机器人管理", b"menu_bot")],
        [Button.inline("🚀 发送指令", b"menu_send")],
        [Button.inline("📊 查看状态", b"menu_status")]
    ]
    if hasattr(event_or_client, 'edit'):
        await event_or_client.edit(text, buttons=buttons)
    else:
        await event_or_client.send_message(chat_id, text, buttons=buttons)

async def send_account_menu(event):
    """账号管理菜单"""
    text = "📱 **账号管理**\n\n请选择操作:"
    buttons = [
        [Button.inline("➕ 添加账号 (交互登录)", b"acc_add_phone")],
        [Button.inline("👁️ 查看账号", b"acc_view")],
        [Button.inline("⬅️ 返回主菜单", b"main_menu")]
    ]
    await event.edit(text, buttons=buttons)

async def send_bot_menu(event):
    """机器人管理菜单"""
    text = "🤖 **签到机器人管理**\n\n请选择操作:"
    buttons = [
        [Button.inline("➕ 添加 bot", b"bot_add")],
        [Button.inline("❌ 删除 bot", b"bot_del")],
        [Button.inline("👁️ 查看 bot", b"bot_view")],
        [Button.inline("⬅️ 返回主菜单", b"main_menu")]
    ]
    await event.edit(text, buttons=buttons)

async def send_cmd_menu(event):
    """指令发送菜单"""
    text = "🚀 **发送指令**\n\n请选择发送方式:"
    buttons = [
        [Button.inline("⚡ 立即发送所有账号", b"send_all_acc")],
        [Button.inline("⬅️ 返回主菜单", b"main_menu")]
    ]
    await event.edit(text, buttons=buttons)

# ============ 5. 事件回调处理 ============

bot = TelegramClient('manager_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    uid = event.sender_id
    if not is_user_allowed(uid):
        await event.answer("⚠️ 当前账号为普通用户, 无法使用该功能。", alert=True)
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
        await event.edit(f"📊 **运行状态**\n\n已托管账号: {a_c}\n已添加机器人: {b_c}", buttons=[Button.inline("⬅️ 返回", b"main_menu")])
    elif data == b"acc_add_phone":
        await event.edit("📱 请输入手机号 (带+86, 例如: +8613800000000)")
        login_process[uid] = {'step': 'get_phone'}
    elif data == b"send_all_acc":
        await event.answer("🚀 正在手动启动全量任务...", alert=False)
        asyncio.create_task(run_all_tasks("手动"))

@bot.on(events.NewMessage)
async def handle_input(event):
    uid = event.sender_id
    text = event.raw_text.strip()

    # --- 1. /start 指令唯一入口 ---
    if text == '/start':
        if is_user_allowed(uid):
            await send_main_menu(bot, uid)
        else:
            await event.reply("🚫 **授权拦截**\n你未获得操作权限, 请联系管理员开通。")
        return

    # --- 2. 管理员授权指令 ---
    if text.startswith('/auth') and uid == ADMIN_ID:
        try:
            target = int(text.split()[1])
            conn = sqlite3.connect('data.db')
            conn.execute('INSERT OR REPLACE INTO authorized_users VALUES (?)', (target,))
            conn.commit(); conn.close()
            await event.reply(f"✅ 已成功授权用户 `{target}`")
        except:
            await event.reply("❌ 格式错误。使用: `/auth 用户ID`")
        return

    if not is_user_allowed(uid):
        return

    # --- 3. 交互登录逻辑 ---
    if uid in login_process:
        state = login_process[uid]
        if state['step'] == 'get_phone':
            phone = text
            c = TelegramClient(os.path.join(SESSION_DIR, phone), API_ID, API_HASH, **DEVICE_CONFIG)
            await c.connect()
            try:
                res = await c.send_code_request(phone)
                login_process[uid] = {'c': c, 'p': phone, 'hash': res.phone_code_hash, 'step': 'get_code'}
                await event.reply("📩 验证码已发送, 请输入 (验证码中间无需空格):")
            except Exception as e:
                await event.reply(f"❌ 错误: {e}"); login_process.pop(uid)
        elif state['step'] == 'get_code':
            try:
                await state['c'].sign_in(state['p'], text, phone_code_hash=state['hash'])
                conn = sqlite3.connect('data.db')
                conn.execute('INSERT OR REPLACE INTO accounts VALUES (?, ?)', (state['p'], uid))
                conn.commit(); conn.close()
                await state['c'].disconnect(); login_process.pop(uid)
                await event.reply(f"🎊 账号 {state['p']} 已成功托管!")
            except SessionPasswordNeededError:
                state['step'] = 'get_pwd'; await event.reply("🔐 该账号开启了二级密码, 请输入:")
            except:
                await event.reply("❌ 验证码错误或已失效"); login_process.pop(uid)
        elif state['step'] == 'get_pwd':
            try:
                await state['c'].sign_in(password=text)
                conn = sqlite3.connect('data.db')
                conn.execute('INSERT OR REPLACE INTO accounts VALUES (?, ?)', (state['p'], uid))
                conn.commit(); conn.close()
                await state['c'].disconnect(); login_process.pop(uid)
                await event.reply("🎊 二级验证成功, 账号已托管!")
            except:
                await event.reply("❌ 密码错误")
        return

    # --- 4. 添加机器人任务逻辑 ---
    if '@' in text and not text.startswith('/'):
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            conn = sqlite3.connect('data.db')
            conn.execute('INSERT INTO bots (username, command, user_id) VALUES (?, ?, ?)', (parts[0], parts[1], uid))
            conn.commit(); conn.close()
            await event.reply(f"✅ 已添加任务:\n机器人: {parts[0]}\n指令: {parts[1]}")

# ============ 6. 运行入口 ============

print(f"📱 伪装设备: iPhone 12 (Swiftgram 12.3)")
print("⏰ 定时设置: 00:05 & 12:05 (每日两次)")
print("💎 机器人已就绪。如果出现重复回复, 请彻底关闭旧进程后再运行。")

# 启动异步定时任务
bot.loop.create_task(custom_scheduler())
# 启动机器人
bot.run_until_disconnected()
