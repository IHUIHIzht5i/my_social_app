import flet as ft

import random
import smtplib
import sqlite3
import re
from email.mime.text import MIMEText
from datetime import datetime

# --- КОНФИГУРАЦИЯ ПОЛЬЗОВАТЕЛЯ ---
SUPER_ADMIN_USERNAME = "alximceo"
SMTP_SENDER = "romaneliseev567@gmail.com"
SMTP_PASSWORD = "xxdt szed clpa heug"

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect("social_ultimate.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY, name TEXT, username TEXT UNIQUE, 
                       email TEXT UNIQUE, password TEXT, 
                       is_admin BOOLEAN DEFAULT 0, is_banned BOOLEAN DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS posts 
                      (id INTEGER PRIMARY KEY, author_id INTEGER, author_name TEXT,
                       content TEXT, image_url TEXT, created_at DATETIME,
                       likes INTEGER DEFAULT 0, FOREIGN KEY(author_id) REFERENCES users(id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS comments 
                      (id INTEGER PRIMARY KEY, post_id INTEGER, author_name TEXT, 
                       text TEXT, created_at DATETIME, FOREIGN KEY(post_id) REFERENCES posts(id))''')
    conn.commit()
    return conn

db_conn = init_db()

# --- ФУНКЦИЯ ОТПРАВКИ ПОЧТЫ ---
def send_otp(email, code):
    msg = MIMEText(f"Ваш секретный код подтверждения для входа в соцсеть: {code}\nНикому не сообщайте его!")
    msg['Subject'] = "Код подтверждения"
    msg['From'] = SMTP_SENDER
    msg['To'] = email
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_SENDER, SMTP_PASSWORD)
            server.sendmail(SMTP_SENDER, email, msg.as_string())
        return True
    except Exception as e:
        print(f"Ошибка отправки почты: {e}")
        return False

def main(page: ft.Page):
    page.title = "Social Pro: alximceo Edition"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 450
    page.padding = 15
    
    session = {"user": None, "otp": None}

    def navigate(view_func):
        page.clean()
        view_func()
        page.update()

    # --- КОМПОНЕНТ: БЕЙДЖ АДМИНА ---
    def get_admin_badge(u_name):
        is_super = (u_name == SUPER_ADMIN_USERNAME)
        color = "amber" if is_super else "blue"
        text = "OWNER" if is_super else "ADMIN"
        
        return ft.Container(
            content=ft.Row([ft.Icon(ft.icons.VERIFIED, color=color, size=14),
                            ft.Text(text, size=10, color=color, weight="bold")], spacing=2),
            padding=ft.padding.symmetric(horizontal=6, vertical=2),
            border=ft.border.all(1, color), border_radius=5
        )

    # --- ЭКРАН: АДМИН-ПАНЕЛЬ ---
    def show_admin_panel():
        user_list = ft.Column(scroll=ft.ScrollMode.ALWAYS, expand=True)

        def toggle_ban(u_id, current_status):
            new_status = 0 if current_status else 1
            db_conn.execute("UPDATE users SET is_banned = ? WHERE id = ?", (new_status, u_id))
            db_conn.commit()
            load_users_admin()

        def load_users_admin():
            user_list.controls.clear()
            cur = db_conn.cursor()
            cur.execute("SELECT id, name, username, is_banned FROM users")
            for u in cur.fetchall():
                u_id, u_name, u_user, u_ban = u
                if u_user == SUPER_ADMIN_USERNAME: continue # Себя банить нельзя
                
                user_list.controls.append(ft.ListTile(
                    title=ft.Text(f"{u_name} (@{u_user})"),
                    trailing=ft.TextButton("РАЗБАНИТЬ" if u_ban else "БАН", 
                                           on_click=lambda e, i=u_id, s=u_ban: toggle_ban(i, s),
                                           style=ft.ButtonStyle(color="red" if not u_ban else "green"))
                ))
            page.update()

        page.add(
            ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda e: navigate(show_feed_screen)),
            ft.Text("Управление пользователями", size=20, weight="bold"),
            user_list
        )
        load_users_admin()

    # --- ЭКРАН: ЛЕНТА ---
    def show_feed_screen():
        posts_col = ft.Column(scroll=ft.ScrollMode.ALWAYS, expand=True)

        def submit_post(e):
            if post_in.value:
                db_conn.execute("INSERT INTO posts (author_id, author_name, content, image_url, created_at) VALUES (?, ?, ?, ?, ?)",
                                (session["user"]["id"], session["user"]["username"], post_in.value, media_in.value, datetime.now()))
                db_conn.commit()
                post_in.value = ""; media_in.value = ""
                load_posts()

        def load_posts(search=""):
            posts_col.controls.clear()
            cur = db_conn.cursor()
            query = "SELECT * FROM posts WHERE content LIKE ? ORDER BY id DESC"
            cur.execute(query, (f"%{search}%",))
            
            for p in cur.fetchall():
                p_id, p_aid, p_aname, p_cont, p_img, p_date, p_likes = p
                
                # Проверка админ-статуса автора
                cur.execute("SELECT is_admin FROM users WHERE username = ?", (p_aname,))
                is_admin = cur.fetchone()[0] or (p_aname == SUPER_ADMIN_USERNAME)

                posts_col.controls.append(ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(p_aname, weight="bold"),
                            get_admin_badge(p_aname) if is_admin else ft.Container(),
                            ft.IconButton(ft.icons.DELETE, icon_color="red", visible=session["user"]["is_admin"],
                                          on_click=lambda e, id=p_id: [db_conn.execute("DELETE FROM posts WHERE id=?", (id,)), db_conn.commit(), load_posts()])
                        ], alignment="spaceBetween"),
                        ft.Text(p_cont),
                        ft.Image(src=p_img, border_radius=10) if p_img else ft.Container(),
                        ft.Text(p_date[:16], size=10, color="grey")
                    ]), padding=15, bgcolor=ft.colors.BLACK12, border_radius=10
                ))
            page.update()

        post_in = ft.TextField(hint_text="Что нового?", multiline=True)
        media_in = ft.TextField(hint_text="URL картинки")
        
        page.add(
            ft.Row([
                ft.Text("SocialNet", size=25, weight="bold"),
                ft.IconButton(ft.icons.SECURITY, on_click=lambda e: navigate(show_admin_panel), visible=session["user"]["is_admin"])
            ], alignment="spaceBetween"),
            ft.Card(content=ft.Container(content=ft.Column([post_in, media_input := media_in, ft.ElevatedButton("Опубликовать", on_click=submit_post)]), padding=10)),
            posts_col
        )
        load_posts()

    # --- ЭКРАН: ВХОД / РЕГИСТРАЦИЯ ---
    def show_auth_screen():
        email_in = ft.TextField(label="Email")
        user_in = ft.TextField(label="Username (для регистрации)")
        pass_in = ft.TextField(label="Пароль", password=True)

        def start_auth(e):
            code = str(random.randint(100000, 999999))
            if send_otp(email_in.value, code):
                session["otp"] = code
                # Проверяем, есть ли юзер в базе
                cur = db_conn.cursor()
                cur.execute("SELECT * FROM users WHERE email = ?", (email_in.value,))
                exists = cur.fetchone()
                
                def verify_code(ee):
                    if otp_in.value == session["otp"]:
                        if not exists:
                            is_adm = 1 if user_in.value == SUPER_ADMIN_USERNAME else 0
                            db_conn.execute("INSERT INTO users (name, username, email, password, is_admin) VALUES (?,?,?,?,?)",
                                            (user_in.value, user_in.value, email_in.value, pass_in.value, is_adm))
                            db_conn.commit()
                        
                        cur.execute("SELECT id, username, is_admin, is_banned FROM users WHERE email = ?", (email_in.value,))
                        u = cur.fetchone()
                        if u[3]: return # Забанен
                        session["user"] = {"id": u[0], "username": u[1], "is_admin": u[2]}
                        navigate(show_feed_screen)

                page.clean()
                otp_in = ft.TextField(label="Введите код из письма")
                page.add(otp_in, ft.ElevatedButton("Подтвердить", on_click=verify_code))
                page.update()

        page.add(
            ft.Text("Добро пожаловать", size=30, weight="bold"),
            email_in, user_in, pass_in,
            ft.ElevatedButton("Войти / Зарегистрироваться", on_click=start_auth)
        )

    show_auth_screen()

ft.app(target=main)
