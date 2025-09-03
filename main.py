import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
import requests
import threading
import time
import uuid
import hashlib
import json
import os
from datetime import datetime
import re
import random
import string

def get_hwid():
    return hashlib.md5(str(uuid.getnode()).encode()).hexdigest()[:8]

def generate_invite_link(length=16):
    """Генерирует случайную ссылку для приглашения"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

class DiscordStyleChat:
    def __init__(self, root):
        self.root = root
        self.root.title("Village Chat • Discord Style")
        self.root.geometry("1200x800")
        self.root.configure(bg="#36393f")
        self.root.minsize(800, 600)
        
        # Конфигурация
        self.bot_token = "8385663546:AAEALoUAR-FlT008PB8sjWpfDCd7gai4JN4"
        self.chat_id = "-1002960597644"
        self.hwid = get_hwid()
        self.username = f"User_{self.hwid}"
        self.last_update_id = 0
        self.is_admin = False
        self.online_users = {}
        self.last_activity = {}
        self.channel_messages = {'global-chat': [], 'bot-dm': []}
        self.current_channel = 'global-chat'
        self.typing_indicators = {}
        self.user_channels = {}  # Хранение каналов пользователей
        self.bot_dm_active = False  # Флаг для личной переписки с ботом
        
        # Цвета Discord
        self.colors = {
            "background": "#36393f",
            "sidebar": "#2f3136",
            "channel_list": "#2f3136",
            "chat_bg": "#36393f",
            "message_bg": "#36393f",
            "input_bg": "#40444b",
            "text_primary": "#ffffff",
            "text_secondary": "#b9bbbe",
            "accent": "#5865f2",
            "online": "#3ba55d",
            "offline": "#747f8d",
            "system": "#ed4245",
            "self_message": "#5865f2",
            "typing": "#72767d",
            "header": "#2f3136",
            "hover": "#3d414d",
            "bot": "#5865f2"
        }
        
        # Загрузка конфигурации
        self.load_config()
        
        self.setup_ui()
        
        # Запуск потоков
        self.update_thread = threading.Thread(target=self.get_messages_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
        
        self.status_thread = threading.Thread(target=self.update_status_loop)
        self.status_thread.daemon = True
        self.status_thread.start()
        
        self.typing_thread = threading.Thread(target=self.update_typing_indicators)
        self.typing_thread.daemon = True
        self.typing_thread.start()
        
        self.display_system_message("Система", "Чат запущен! Добро пожаловать в Village Chat!")
        self.send_presence()
        self.send_telegram_message(f"Пользователь {self.username} присоединился к чату")
    
    def update_status_loop(self):
        while True:
            try:
                # Проверяем активность пользователей
                current_time = datetime.now()
                for hwid, user_data in self.online_users.copy().items():
                    if (current_time - user_data['last_seen']).seconds > 120:
                        self.online_users[hwid]['status'] = 'idle'
                
                self.update_online_counter()
                time.sleep(10)
                
            except Exception as e:
                print(f"Ошибка в update_status_loop: {e}")
                time.sleep(10)
    
    def load_config(self):
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r") as f:
                    config = json.load(f)
                    self.username = config.get('username', self.username)
                    self.user_channels = config.get('user_channels', {})
        except Exception as e:
            print(f"Ошибка загрузки конфигурации: {e}")
    
    def save_config(self):
        try:
            with open("config.json", "w") as f:
                json.dump({'username': self.username, 'user_channels': self.user_channels}, f)
        except Exception as e:
            print(f"Ошибка сохранения конфигурации: {e}")
    
    def setup_ui(self):
        # Главный контейнер
        main_frame = tk.Frame(self.root, bg=self.colors["background"])
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Боковая панель серверов (слева)
        server_sidebar = tk.Frame(main_frame, bg=self.colors["sidebar"], width=70)
        server_sidebar.pack(side=tk.LEFT, fill=tk.Y)
        server_sidebar.pack_propagate(False)
        
        # Сервер иконка
        server_icon = tk.Label(server_sidebar, text="VC", font=("Arial", 16, "bold"), 
                              bg=self.colors["accent"], fg="white", width=4, height=2,
                              cursor="hand2", relief="flat")
        server_icon.pack(pady=15)
        server_icon.bind("<Button-1>", lambda e: self.show_server_info())
        server_icon.bind("<Enter>", lambda e: server_icon.config(bg="#4752c4"))
        server_icon.bind("<Leave>", lambda e: server_icon.config(bg=self.colors["accent"]))
        
        # Разделитель
        separator = tk.Frame(server_sidebar, bg="#202225", height=2)
        separator.pack(fill=tk.X, pady=10)
        
        # Основная панель
        main_content = tk.Frame(main_frame, bg=self.colors["background"])
        main_content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Панель каналов и пользователей
        left_sidebar = tk.Frame(main_content, bg=self.colors["channel_list"], width=240)
        left_sidebar.pack(side=tk.LEFT, fill=tk.Y)
        left_sidebar.pack_propagate(False)
        
        # Заголовок канала
        channel_header = tk.Frame(left_sidebar, bg=self.colors["header"], height=50)
        channel_header.pack(fill=tk.X)
        
        server_name = tk.Label(channel_header, text="Village Chat", font=("Arial", 16, "bold"), 
                bg=self.colors["header"], fg="white")
        server_name.pack(side=tk.LEFT, padx=15)
        
        # Кнопка настроек
        settings_btn = tk.Label(channel_header, text="⚙️", font=("Arial", 14), 
                               bg=self.colors["header"], fg="white", cursor="hand2")
        settings_btn.pack(side=tk.RIGHT, padx=15)
        settings_btn.bind("<Button-1>", lambda e: self.show_settings())
        settings_btn.bind("<Enter>", lambda e: settings_btn.config(bg=self.colors["hover"]))
        settings_btn.bind("<Leave>", lambda e: settings_btn.config(bg=self.colors["header"]))
        
        # Список каналов
        channels_frame = tk.Frame(left_sidebar, bg=self.colors["channel_list"])
        channels_frame.pack(fill=tk.X, pady=10)
        
        # Категория текстовых каналов
        category_frame = tk.Frame(channels_frame, bg=self.colors["channel_list"])
        category_frame.pack(fill=tk.X, padx=15, pady=(10, 5))
        
        tk.Label(category_frame, text="ТЕКСТОВЫЕ КАНАЛЫ", font=("Arial", 10, "bold"), 
                bg=self.colors["channel_list"], fg=self.colors["text_secondary"]).pack(anchor="w")
        
        # Каналы
        channel_frame = tk.Frame(channels_frame, bg=self.colors["channel_list"])
        channel_frame.pack(fill=tk.X, padx=15, pady=2)
        
        # Global chat
        global_channel = tk.Label(channel_frame, text="# global-chat", font=("Arial", 12), 
                                 bg=self.colors["channel_list"], fg="white", 
                                 cursor="hand2", anchor="w")
        global_channel.pack(fill=tk.X, pady=2)
        global_channel.bind("<Button-1>", lambda e: self.switch_channel('global-chat'))
        global_channel.bind("<Enter>", lambda e: global_channel.config(bg=self.colors["hover"]))
        global_channel.bind("<Leave>", lambda e: global_channel.config(bg=self.colors["channel_list"]))
        
        # Bot DM channel
        bot_channel = tk.Label(channel_frame, text="🤖 bot-dm", font=("Arial", 12), 
                              bg=self.colors["channel_list"], fg=self.colors["text_primary"], 
                              cursor="hand2", anchor="w")
        bot_channel.pack(fill=tk.X, pady=2)
        bot_channel.bind("<Button-1>", lambda e: self.switch_to_bot_dm())
        bot_channel.bind("<Enter>", lambda e: bot_channel.config(bg=self.colors["hover"], fg="white"))
        bot_channel.bind("<Leave>", lambda e: bot_channel.config(bg=self.colors["channel_list"], fg=self.colors["text_primary"]))
        
        # User channels
        for channel_name in self.user_channels.keys():
            user_ch = tk.Label(channel_frame, text=f"# {channel_name}", font=("Arial", 12), 
                              bg=self.colors["channel_list"], fg=self.colors["text_primary"], 
                              cursor="hand2", anchor="w")
            user_ch.pack(fill=tk.X, pady=2)
            user_ch.bind("<Button-1>", lambda e, ch=channel_name: self.switch_channel(ch))
            user_ch.bind("<Enter>", lambda e, ch=user_ch: ch.config(bg=self.colors["hover"], fg="white"))
            user_ch.bind("<Leave>", lambda e, ch=user_ch: ch.config(bg=self.colors["channel_list"], fg=self.colors["text_primary"]))
        
        # Разделитель
        separator2 = tk.Frame(left_sidebar, bg="#202225", height=1)
        separator2.pack(fill=tk.X, pady=10)
        
        # Список онлайн-пользователей
        online_frame = tk.Frame(left_sidebar, bg=self.colors["channel_list"])
        online_frame.pack(fill=tk.BOTH, expand=True)
        
        online_header = tk.Frame(online_frame, bg=self.colors["channel_list"])
        online_header.pack(fill=tk.X, pady=(10, 5))
        
        tk.Label(online_header, text="ОНЛАЙН", font=("Arial", 10, "bold"), 
                bg=self.colors["channel_list"], fg=self.colors["text_secondary"]).pack(side=tk.LEFT, padx=15)
        
        self.online_count_label = tk.Label(online_header, text="0", font=("Arial", 10), 
                                         bg=self.colors["channel_list"], fg=self.colors["text_secondary"])
        self.online_count_label.pack(side=tk.RIGHT, padx=15)
        
        self.online_listbox = tk.Listbox(online_frame, bg=self.colors["channel_list"], fg="white",
                                        font=("Arial", 11), bd=0, highlightthickness=0,
                                        selectbackground=self.colors["accent"])
        self.online_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Пользовательская информация
        user_frame = tk.Frame(left_sidebar, bg=self.colors["channel_list"], height=60)
        user_frame.pack(fill=tk.X, side=tk.BOTTOM)
        user_frame.pack_propagate(False)
        
        user_inner = tk.Frame(user_frame, bg=self.colors["hover"])
        user_inner.pack(fill=tk.BOTH, padx=10, pady=10)
        
        avatar = tk.Label(user_inner, text="👤", font=("Arial", 14), 
                         bg=self.colors["hover"], fg="white")
        avatar.pack(side=tk.LEFT, padx=5)
        
        user_info = tk.Frame(user_inner, bg=self.colors["hover"])
        user_info.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        username_label = tk.Label(user_info, text=self.username, font=("Arial", 11, "bold"), 
                                 bg=self.colors["hover"], fg="white", anchor="w")
        username_label.pack(fill=tk.X)
        
        status_label = tk.Label(user_info, text="Online", font=("Arial", 10), 
                               bg=self.colors["hover"], fg=self.colors["online"], anchor="w")
        status_label.pack(fill=tk.X)
        
        # Основная область чата
        chat_area_main = tk.Frame(main_content, bg=self.colors["chat_bg"])
        chat_area_main.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Заголовок чата
        chat_header = tk.Frame(chat_area_main, bg=self.colors["header"], height=50)
        chat_header.pack(fill=tk.X)
        
        # Хэштег канала
        self.channel_label = tk.Label(chat_header, text="# general", font=("Arial", 16, "bold"), 
                                     bg=self.colors["header"], fg="white")
        self.channel_label.pack(side=tk.LEFT, padx=20)
        
        # Индикатор набора сообщения
        self.typing_label = tk.Label(chat_header, text="", font=("Arial", 10, "italic"), 
                                    bg=self.colors["header"], fg=self.colors["text_secondary"])
        self.typing_label.pack(side=tk.LEFT, padx=10)
        
        # Кнопки управления чатом
        controls_frame = tk.Frame(chat_header, bg=self.colors["header"])
        controls_frame.pack(side=tk.RIGHT, padx=10)
        
        search_btn = tk.Label(controls_frame, text="🔍", font=("Arial", 14), 
                             bg=self.colors["header"], fg="white", cursor="hand2")
        search_btn.pack(side=tk.LEFT, padx=5)
        search_btn.bind("<Enter>", lambda e: search_btn.config(bg=self.colors["hover"]))
        search_btn.bind("<Leave>", lambda e: search_btn.config(bg=self.colors["header"]))
        
        pin_btn = tk.Label(controls_frame, text="📌", font=("Arial", 14), 
                          bg=self.colors["header"], fg="white", cursor="hand2")
        pin_btn.pack(side=tk.LEFT, padx=5)
        pin_btn.bind("<Enter>", lambda e: pin_btn.config(bg=self.colors["hover"]))
        pin_btn.bind("<Leave>", lambda e: pin_btn.config(bg=self.colors["header"]))
        
        members_btn = tk.Label(controls_frame, text="👥", font=("Arial", 14), 
                              bg=self.colors["header"], fg="white", cursor="hand2")
        members_btn.pack(side=tk.LEFT, padx=5)
        members_btn.bind("<Enter>", lambda e: members_btn.config(bg=self.colors["hover"]))
        members_btn.bind("<Leave>", lambda e: members_btn.config(bg=self.colors["header"]))
        
        # Область сообщений
        messages_frame = tk.Frame(chat_area_main, bg=self.colors["chat_bg"])
        messages_frame.pack(fill=tk.BOTH, expand=True)
        
        # Контейнер для сообщений с прокруткой
        self.messages_container = scrolledtext.ScrolledText(messages_frame, bg=self.colors["chat_bg"], 
                                                           fg=self.colors["text_primary"], font=("Arial", 11),
                                                           wrap=tk.WORD, bd=0, highlightthickness=0,
                                                           state=tk.DISABLED, padx=20, pady=10)
        self.messages_container.pack(fill=tk.BOTH, expand=True)
        
        # Настройка тегов для форматирования
        self.messages_container.tag_config("system", foreground=self.colors["system"])
        self.messages_container.tag_config("self", foreground=self.colors["self_message"])
        self.messages_container.tag_config("username", foreground=self.colors["accent"], font=("Arial", 12, "bold"))
        self.messages_container.tag_config("time", foreground=self.colors["text_secondary"], font=("Arial", 10))
        self.messages_container.tag_config("mention", foreground="#ff7c7c", background="#3d414d")
        self.messages_container.tag_config("bot", foreground=self.colors["bot"], font=("Arial", 12, "bold"))
        
        # Панель ввода
        input_frame = tk.Frame(chat_area_main, bg=self.colors["input_bg"], height=80)
        input_frame.pack(fill=tk.X)
        input_frame.pack_propagate(False)
        
        input_inner = tk.Frame(input_frame, bg=self.colors["input_bg"])
        input_inner.pack(fill=tk.BOTH, padx=20, pady=15)
        
        # Кнопка добавления вложений
        attach_btn = tk.Label(input_inner, text="➕", font=("Arial", 14), 
                             bg=self.colors["input_bg"], fg="white", cursor="hand2")
        attach_btn.pack(side=tk.LEFT, padx=(0, 10))
        attach_btn.bind("<Enter>", lambda e: attach_btn.config(bg=self.colors["hover"]))
        attach_btn.bind("<Leave>", lambda e: attach_btn.config(bg=self.colors["input_bg"]))
        
        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(
            input_inner,
            textvariable=self.input_var,
            font=("Arial", 12),
            bg=self.colors["input_bg"],
            fg="white",
            insertbackground="white",
            relief=tk.FLAT,
            bd=0
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self.input_entry.bind("<Return>", self.send_message)
        self.input_entry.bind("<Key>", self.user_typing)
        self.input_entry.bind("<KeyRelease>", self.user_stopped_typing)
        
        # Кнопка отправки
        send_btn = tk.Button(
            input_inner,
            text="➤",
            font=("Arial", 14),
            bg=self.colors["accent"],
            fg="white",
            relief=tk.FLAT,
            bd=0,
            width=3,
            command=self.send_message,
            cursor="hand2"
        )
        send_btn.pack(side=tk.RIGHT)
        send_btn.bind("<Enter>", lambda e: send_btn.config(bg="#4752c4"))
        send_btn.bind("<Leave>", lambda e: send_btn.config(bg=self.colors["accent"]))
        
        # Прокрутка вниз при новом сообщении
        self.auto_scroll = True
    
    def switch_to_bot_dm(self):
        """Переключение в личную переписку с ботом"""
        self.bot_dm_active = True
        self.current_channel = 'bot-dm'
        self.channel_label.config(text="🤖 bot-dm")
        self.clear_messages()
        
        # Загружаем сообщения для канала
        for msg in self.channel_messages.get('bot-dm', []):
            self.display_message_locally(msg['username'], msg['content'], msg['type'], msg.get('avatar', '👤'))
        
        # Приветственное сообщение от бота
        self.display_bot_message("Бот", "Добро пожаловать в личную переписку! Отправьте /help для списка команд.")
    
    def display_bot_message(self, username, content):
        """Отображает сообщение от бота"""
        self.display_message_locally(username, content, "bot", "🤖")
    
    def process_bot_command(self, command):
        """Обработка команд для бота"""
        if command.startswith("/create channel:"):
            # Обработка создания канала
            try:
                parts = command.split("channel:")[1].split("invite-link:")
                channel_name = parts[0].strip()
                invite_link = parts[1].strip() if len(parts) > 1 else ""
                
                # Генерируем channel_id и пригласительную ссылку
                channel_id = f"-100{random.randint(100000000, 999999999)}"
                invite_token = generate_invite_link()
                final_invite_link = f"https://t.me/+{invite_token}"
                
                # Сохраняем канал
                self.user_channels[channel_name] = {
                    'channel_id': channel_id,
                    'invite_link': final_invite_link,
                    'created': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'telegram_link': invite_link
                }
                
                # Сохраняем конфигурацию
                self.save_config()
                
                # Обновляем UI
                self.update_channel_list()
                
                # Отправляем ответ
                response = f"Канал '{channel_name}' успешно создан!\n\n"
                response += f"ID канала: {channel_id}\n"
                response += f"Пригласительная ссылка: {final_invite_link}\n"
                if invite_link:
                    response += f"Исходная ссылка Telegram: {invite_link}"
                
                self.display_bot_message("Бот", response)
                
            except Exception as e:
                self.display_bot_message("Бот", f"Ошибка при создании канала: {str(e)}")
        
        elif command == "/help":
            help_text = "Доступные команды:\n\n"
            help_text += "/create channel:NAME invite-link:URL - Создать новый канал\n"
            help_text += "/my_channels - Показать мои каналы\n"
            help_text += "/help - Показать эту справку"
            self.display_bot_message("Бот", help_text)
        
        elif command == "/my_channels":
            if not self.user_channels:
                self.display_bot_message("Бот", "У вас нет созданных каналов.")
            else:
                channels_text = "Ваши каналы:\n\n"
                for name, info in self.user_channels.items():
                    channels_text += f"📢 {name}\n"
                    channels_text += f"   ID: {info['channel_id']}\n"
                    channels_text += f"   Ссылка: {info['invite_link']}\n"
                    channels_text += f"   Создан: {info['created']}\n\n"
                self.display_bot_message("Бот", channels_text)
        
        else:
            self.display_bot_message("Бот", "Неизвестная команда. Отправьте /help для списка команд.")
    
    def update_channel_list(self):
        """Обновляет список каналов в UI"""
        # Эта функция требует переработки UI, поэтому просто сохраняем конфиг
        self.save_config()
    
    def show_server_info(self):
        info = f"Версия: 1.0\nПользователь: {self.username}\nID: {self.hwid}\nОнлайн: {len(self.online_users)}"
        messagebox.showinfo("Информация о сервере", info)
    
    def show_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Настройки")
        settings_window.geometry("400x300")
        settings_window.configure(bg=self.colors["background"])
        settings_window.resizable(False, False)
        
        tk.Label(settings_window, text="Настройки пользователя", font=("Arial", 16, "bold"), 
                bg=self.colors["background"], fg="white").pack(pady=20)
        
        tk.Label(settings_window, text="Имя пользователя:", font=("Arial", 12), 
                bg=self.colors["background"], fg="white").pack(anchor="w", padx=20)
        
        username_var = tk.StringVar(value=self.username)
        username_entry = tk.Entry(settings_window, textvariable=username_var, font=("Arial", 12),
                                 bg=self.colors["input_bg"], fg="white", insertbackground="white")
        username_entry.pack(fill=tk.X, padx=20, pady=10)
        
        def save_settings():
            new_username = username_var.get().strip()
            if new_username and new_username != self.username:
                self.username = new_username
                self.save_config()
                self.send_telegram_message(f"Пользователь {self.hwid} сменил имя на {self.username}")
                settings_window.destroy()
                messagebox.showinfo("Успех", "Настройки сохранены")
        
        save_btn = tk.Button(settings_window, text="Сохранить", font=("Arial", 12),
                            bg=self.colors["accent"], fg="white", command=save_settings)
        save_btn.pack(pady=20)
    
    def switch_channel(self, channel_name):
        self.bot_dm_active = False
        self.current_channel = channel_name
        self.channel_label.config(text=f"# {channel_name}")
        self.clear_messages()
        
        # Загружаем сообщения для канала
        for msg in self.channel_messages.get(channel_name, []):
            self.display_message_locally(msg['username'], msg['content'], msg['type'], msg.get('avatar', '👤'))
    
    def clear_messages(self):
        self.messages_container.config(state=tk.NORMAL)
        self.messages_container.delete(1.0, tk.END)
        self.messages_container.config(state=tk.DISABLED)
    
    def user_typing(self, event):
        self.last_activity[self.hwid] = datetime.now()
        if event.keysym not in ["Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R"]:
            self.send_typing_status(True)
    
    def user_stopped_typing(self, event):
        threading.Timer(2.0, self.send_typing_status, [False]).start()
    
    def send_typing_status(self, typing):
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendChatAction"
            params = {'chat_id': self.chat_id, 'action': 'typing' if typing else 'cancel'}
            requests.post(url, params=params, timeout=5)
        except Exception as e:
            print(f"Ошибка отправки статуса набора: {e}")
    
    def update_typing_indicators(self):
        while True:
            try:
                current_time = datetime.now()
                expired_typers = []
                
                for user, typing_data in self.typing_indicators.items():
                    if (current_time - typing_data['time']).seconds > 3:
                        expired_typers.append(user)
                
                for user in expired_typers:
                    del self.typing_indicators[user]
                
                self.update_typing_display()
                time.sleep(1)
            except Exception as e:
                print(f"Ошибка в update_typing_indicators: {e}")
                time.sleep(5)
    
    def update_typing_display(self):
        if self.typing_indicators:
            typers = list(self.typing_indicators.keys())
            if len(typers) == 1:
                text = f"{typers[0]} печатает..."
            elif len(typers) == 2:
                text = f"{typers[0]} и {typers[1]} печатают..."
            else:
                text = f"{len(typers)} пользователей печатают..."
            self.typing_label.config(text=text)
        else:
            self.typing_label.config(text="")
    
    def update_online_counter(self):
        online_count = len([u for u in self.online_users.values() if u['status'] == 'online'])
        self.online_count_label.config(text=str(online_count))
        
        # Обновляем список онлайн
        self.online_listbox.delete(0, tk.END)
        for hwid, user_data in self.online_users.items():
            status = "🟢" if user_data['status'] == 'online' else "🟡"
            self.online_listbox.insert(tk.END, f"   {status} {user_data['username']} ({hwid})")
    
    def send_presence(self):
        self.last_activity[self.hwid] = datetime.now()
        self.online_users[self.hwid] = {
            'username': self.username,
            'last_seen': datetime.now(),
            'status': 'online'
        }
        self.update_online_counter()
    
    def display_message_locally(self, username, content, message_type="user", avatar="👤"):
        self.messages_container.config(state=tk.NORMAL)
        
        # Время сообщения
        timestamp = datetime.now().strftime("%H:%M")
        
        # Форматируем сообщение
        if message_type == "system":
            self.messages_container.insert(tk.END, f"[{timestamp}] ", "time")
            self.messages_container.insert(tk.END, f"{username}: ", "system")
            self.messages_container.insert(tk.END, f"{content}\n\n")
        elif message_type == "self":
            self.messages_container.insert(tk.END, f"[{timestamp}] ", "time")
            self.messages_container.insert(tk.END, f"{username}: ", "self")
            
            # Обработка упоминаний
            formatted_content = self.format_mentions(content)
            self.messages_container.insert(tk.END, f"{formatted_content}\n\n")
        elif message_type == "bot":
            self.messages_container.insert(tk.END, f"[{timestamp}] ", "time")
            self.messages_container.insert(tk.END, f"{username}: ", "bot")
            self.messages_container.insert(tk.END, f"{content}\n\n")
        else:
            self.messages_container.insert(tk.END, f"[{timestamp}] ", "time")
            self.messages_container.insert(tk.END, f"{username}: ", "username")
            
            # Обработка упоминаний
            formatted_content = self.format_mentions(content)
            self.messages_container.insert(tk.END, f"{formatted_content}\n\n")
        
        # Прокрутка вниз если включена авто-прокрутка
        if self.auto_scroll:
            self.messages_container.see(tk.END)
        
        self.messages_container.config(state=tk.DISABLED)
    
    def format_mentions(self, text):
        # Ищем упоминания вида @#HWID
        mention_pattern = r'@#(\w+)'
        mentions = re.findall(mention_pattern, text)
        
        for mention in mentions:
            if mention == self.hwid:
                replacement = f"@{self.username}"
                text = text.replace(f"@#{mention}", replacement)
        
        return text
    
    def display_system_message(self, username, content):
        self.display_message_locally(username, content, "system", "⚙️")
    
    def send_message(self, event=None):
        text = self.input_var.get().strip()
        if text:
            if self.bot_dm_active:
                # Обработка команд для бота
                if text.startswith("/"):
                    self.process_bot_command(text)
                else:
                    self.display_message_locally("Вы", text, "self", "👤")
                    self.display_bot_message("Бот", "Я не понимаю обычные сообщения. Используйте команды, начиная с /")
                
                # Сохраняем сообщение в истории канала
                if 'bot-dm' not in self.channel_messages:
                    self.channel_messages['bot-dm'] = []
                
                self.channel_messages['bot-dm'].append({
                    'username': 'Вы',
                    'content': text,
                    'type': 'self',
                    'avatar': '👤'
                })
            else:
                if text.startswith("/"):
                    self.process_command(text)
                else:
                    full_message = f"[{self.current_channel}][{self.hwid}][{self.username}] {text}"
                    self.send_telegram_message(full_message)
                    self.display_message_locally("Вы", text, "self", "👤")
                    
                    # Сохраняем сообщение в истории канала
                    if self.current_channel not in self.channel_messages:
                        self.channel_messages[self.current_channel] = []
                    
                    self.channel_messages[self.current_channel].append({
                        'username': 'Вы',
                        'content': text,
                        'type': 'self',
                        'avatar': '👤'
                    })
            
            self.input_var.set("")
            self.send_presence()
    
    def process_command(self, command):
        if command == "/clear":
            self.clear_messages()
            self.display_system_message("Система", "Чат очищен")
        elif command == "/online":
            online_list = "\n".join([f"• {user['username']} ({hwid})" for hwid, user in self.online_users.items()])
            self.display_system_message("Онлайн", f"Пользователи онлайн:\n{online_list}")
        elif command.startswith("/nick "):
            new_username = command[6:].strip()
            if new_username:
                old_username = self.username
                self.username = new_username
                self.save_config()
                self.send_telegram_message(f"Пользователь {self.hwid} сменил имя с {old_username} на {self.username}")
                self.display_system_message("Система", f"Имя пользователя изменено на {self.username}")
        elif command == "/bot":
            self.switch_to_bot_dm()
        else:
            self.display_system_message("Система", "Неизвестная команда")
    
    def send_telegram_message(self, text, chat_id=None):
        if chat_id is None:
            chat_id = self.chat_id
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            params = {'chat_id': chat_id, 'text': text}
            requests.post(url, params=params, timeout=10)
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")
    
    def get_messages_loop(self):
        while True:
            try:
                url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
                params = {'offset': self.last_update_id + 1, 'timeout': 30}
                
                response = requests.get(url, params=params, timeout=35).json()
                
                if response['ok']:
                    for update in response['result']:
                        self.last_update_id = update['update_id']
                        message = update.get('message', {})
                        
                        if 'text' in message:
                            text = message['text']
                            from_user = message.get('from', {})
                            username = from_user.get('first_name', 'Unknown')
                            
                            # Парсим наше специальное форматирование
                            if text.startswith('[') and ']' in text:
                                parts = text.split(']', 2)
                                if len(parts) >= 3:
                                    channel = parts[0][1:]  # Убираем начальную [
                                    hwid_part = parts[1][1:] if parts[1].startswith('[') else parts[1]
                                    username_part = parts[2][1:] if parts[2].startswith('[') else parts[2]
                                    
                                    # Извлекаем HWID и имя пользователя
                                    if '[' in hwid_part and ']' in hwid_part:
                                        hwid = hwid_part.split('[')[1].split(']')[0]
                                        user_msg_username = username_part.split(']')[0] if ']' in username_part else username
                                        message_text = text.split(']', 3)[3].strip() if len(text.split(']', 3)) > 3 else text
                                        
                                        # Обновляем активность
                                        self.last_activity[hwid] = datetime.now()
                                        if hwid not in self.online_users:
                                            self.online_users[hwid] = {
                                                'username': user_msg_username,
                                                'last_seen': datetime.now(),
                                                'status': 'online'
                                            }
                                        else:
                                            self.online_users[hwid]['last_seen'] = datetime.now()
                                            self.online_users[hwid]['status'] = 'online'
                                        
                                        self.update_online_counter()
                                        
                                        # Отображаем сообщения только для текущего канала
                                        if channel == self.current_channel:
                                            if hwid == self.hwid:
                                                # Это наше сообщение, уже показано локально
                                                pass
                                            else:
                                                self.display_message_locally(user_msg_username, message_text, "user", "👤")
                                                
                                                # Сохраняем сообщение в истории канала
                                                if channel not in self.channel_messages:
                                                    self.channel_messages[channel] = []
                                                
                                                self.channel_messages[channel].append({
                                                    'username': user_msg_username,
                                                    'content': message_text,
                                                    'type': 'user',
                                                    'avatar': '👤'
                                                })
                                        continue
                            
                            # Обычные сообщения (не из нашего чата)
                            if 'from' in message:
                                sender_hwid = None
                                if f"[" in text and "]" in text:
                                    start = text.find("[") + 1
                                    end = text.find("]")
                                    if start < end:
                                        sender_hwid = text[start:end]
                                        self.last_activity[sender_hwid] = datetime.now()
                                        if sender_hwid not in self.online_users:
                                            self.online_users[sender_hwid] = {
                                                'username': f"User_{sender_hwid}",
                                                'last_seen': datetime.now(),
                                                'status': 'online'
                                            }
                                        else:
                                            self.online_users[sender_hwid]['last_seen'] = datetime.now()
                                            self.online_users[sender_hwid]['status'] = 'online'
                                        self.update_online_counter()
                            
                            # Пропускаем админ-команды
                            if text.startswith("[admin]"):
                                continue
                            
                            # Отображаем сообщения
                            if f"[{self.hwid}]" in text:
                                display_text = text.replace(f"[{self.hwid}]", "").strip()
                                self.display_message_locally("Вы", display_text, "self", "👤")
                            else:
                                self.display_message_locally(username, text, "user", "👤")
            
            except Exception as e:
                print(f"Ошибка в get_messages_loop: {e}")
                time.sleep(5)

if __name__ == "__main__":
    root = tk.Tk()
    app = DiscordStyleChat(root)
    root.mainloop()