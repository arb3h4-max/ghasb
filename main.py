import flet as ft
import os
import threading
import yt_dlp
import re

# ---------- وظائف مساعدة ----------
def find_cookie_files():
    candidates = ["/storage/emulated/0/Download", "/sdcard/Download"]
    out = []
    for path in candidates:
        try:
            if os.path.isdir(path):
                for f in os.listdir(path):
                    if ("cookie" in f.lower()) and f.endswith((".txt", ".json")):
                        out.append(os.path.join(path, f))
        except: pass
    return sorted(list(set(out)))

def main(page: ft.Page):
    page.title = "تحميل غصب PRO"
    page.theme_mode = ft.ThemeMode.DARK
    page.rtl = True
    page.padding = 15
    page.scroll = ft.ScrollMode.AUTO

    state = {"path": "/storage/emulated/0/Download/GhasabApp"}

    # ---------- عناصر الواجهة ----------
    url_input = ft.TextField(
        label="روابط الفيديو",
        multiline=True,
        min_lines=1,
        max_lines=3,
        border_radius=12,
        hint_text="ضع الروابط هنا..."
    )

    path_input = ft.TextField(
        label="مسار الحفظ",
        value=state["path"],
        border_radius=10,
        text_size=12,
        expand=True
    )

    video_thumbnail = ft.Image(
        src="https://flet.dev/img/pages/quickstart/flet-app-icons.png",
        width=300,
        height=180,
        fit="contain", 
        border_radius=10,
        visible=False
    )

    cookies_dropdown = ft.Dropdown(
        label="ملف الكوكيز (اختياري)",
        options=[ft.dropdown.Option(key=f, text=os.path.basename(f)) for f in find_cookie_files()],
        expand=True
    )

    progress_bar = ft.ProgressBar(value=0, expand=True, color=ft.Colors.BLUE_400)
    progress_text = ft.Text("التقدم: 0%", size=12)
    log_list = ft.ListView(expand=True, spacing=5, auto_scroll=True)
    
    status_text = ft.Text("جاهز للتحميل", weight="bold")

    # ---------- وظائف المنطق ----------
    def append_log(msg):
        log_list.controls.append(ft.Text(msg, size=11, color=ft.Colors.GREY_300))
        page.update()

    def update_path(e):
        state["path"] = path_input.value.strip()
        os.makedirs(state["path"], exist_ok=True)
        page.snack_bar = ft.SnackBar(ft.Text("✅ تم حفظ المسار الجديد"))
        page.snack_bar.open = True
        page.update()

    def update_progress(d):
        if d['status'] == 'downloading':
            try:
                p_raw = d.get('_percent_str', '0%').replace('%','')
                progress_bar.value = float(p_raw) / 100
                progress_text.value = f"جاري التحميل: {p_raw}%"
                page.update()
            except: pass

    def start_download(e):
        urls = [u.strip() for u in url_input.value.split('\n') if u.strip()]
        if not urls:
            page.snack_bar = ft.SnackBar(ft.Text("❌ ضع رابطاً أولاً"))
            page.snack_bar.open = True
            page.update()
            return
        
        mode = e.control.data 
        cookie_file = cookies_dropdown.value
        
        def dl_thread():
            save_path = state["path"]
            os.makedirs(save_path, exist_ok=True)
            
            # تسجيل ملف الكوكيز المستخدم
            if cookie_file:
                append_log(f"🍪 الكوكيز المستخدم: {os.path.basename(cookie_file)}")
            else:
                append_log("ℹ️ التحميل بدون ملف كوكيز")

            for url in urls:
                append_log(f"🔍 فحص الرابط: {url}")
                
                try:
                    # 1. جلب معلومات الفيديو أولاً بدون تحميل
                    with yt_dlp.YoutubeDL({'quiet': True, 'cookiefile': cookie_file}) as ydl_info:
                        info = ydl_info.extract_info(url, download=False)
                        
                        # تحديث الصورة في الواجهة
                        video_thumbnail.src = info.get('thumbnail', "")
                        video_thumbnail.visible = True
                        
                        raw_title = info.get('title', 'video')
                        # تنظيف العنوان من الرموز غير المسموحة في أسماء الملفات
                        clean_title = re.sub(r'[\\/:*?"<>|]+', "", raw_title)
                        
                        # ميزة الترقيم التلقائي (إضافة رقم في حال وجود ملف بنفس الاسم)
                        final_title = clean_title
                        counter = 1
                        # نتحقق من وجود أي ملف يبدأ بهذا الاسم في المجلد
                        while any(f.startswith(final_title + ".") or f.startswith(final_title + " (") for f in os.listdir(save_path)):
                            # إذا كان الملف موجود فعلاً (وليس مجرد بداية اسم متشابهة)
                            file_ext = ".mp4" if mode == "video" else ".mp3"
                            if os.path.exists(os.path.join(save_path, final_title + file_ext)):
                                final_title = f"{clean_title} ({counter})"
                                counter += 1
                            else:
                                break
                        
                        append_log(f"📄 الاسم النهائي: {final_title}")
                        
                        # خيارات التحميل مع الترقيم والبوستر
                        opts = {
                            'outtmpl': f"{save_path}/{final_title}.%(ext)s",
                            'no_overwrites': True,
                            'format': 'bestvideo+bestaudio/best' if mode == 'video' else 'bestaudio/best',
                            'progress_hooks': [update_progress],
                            'cookiefile': cookie_file,
                            'writethumbnail': True,
                            'postprocessors': [{
                                'key': 'EmbedThumbnail',
                                'already_have_thumbnail': False,
                            }],
                        }
                        
                        status_text.value = f"جاري تحميل: {final_title[:20]}..."
                        page.update()
                        
                        # 2. البدء بالتحميل الفعلي
                        with yt_dlp.YoutubeDL(opts) as ydl:
                            ydl.download([url])
                        
                    append_log(f"✅ تم بنجاح: {final_title}")
                except Exception as ex:
                    append_log(f"❌ خطأ: {str(ex)[:100]}")
            
            # مسح الروابط تلقائياً وتصفير العداد
            url_input.value = ""
            status_text.value = "اكتملت جميع العمليات!"
            progress_bar.value = 0
            page.update()

        threading.Thread(target=dl_thread, daemon=True).start()

    # ---------- بناء الصفحة ----------
    page.add(
        ft.Container(
            padding=15, border_radius=20, bgcolor=ft.Colors.BLACK_12,
            content=ft.Column([
                ft.Text("تحميل غصب PRO", size=26, weight="bold", color=ft.Colors.BLUE_400),
                
                ft.Row([video_thumbnail], alignment="center"),
                
                url_input,
                
                ft.Row([
                    path_input,
                    ft.IconButton(ft.Icons.SAVE, on_click=update_path, tooltip="حفظ المسار"),
                ]),
                
                cookies_dropdown,
                
                ft.Row([
                    ft.FilledButton("فيديو + بوستر", data="video", icon=ft.Icons.DOWNLOAD, on_click=start_download, expand=True),
                    ft.FilledButton("صوت + بوستر", data="audio", icon=ft.Icons.MUSIC_NOTE, on_click=start_download, expand=True, bgcolor=ft.Colors.GREEN_800),
                ]),
                
                ft.Divider(height=10),
                status_text,
                progress_bar, 
                progress_text,
                
                ft.Container(
                    content=log_list, 
                    height=180, 
                    bgcolor=ft.Colors.BLACK_26, 
                    padding=10, 
                    border_radius=12,
                    border=ft.border.all(1, ft.Colors.GREY_900)
                ),
            ], horizontal_alignment="center")
        )
    )

if __name__ == "__main__":
    ft.run(main)