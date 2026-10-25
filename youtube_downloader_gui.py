import tkinter as tk
from tkinter import filedialog, messagebox
import yt_dlp
import threading
import os
import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class YouTubeDownloader:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("YouTube Downloader — Вибір якості")
        self.root.geometry("760x580")
        self.root.resizable(True, True)

        self.url_var = ctk.StringVar()
        self.save_path = os.path.expanduser("~/Downloads")
        self.is_downloading = False

        self.create_widgets()

    def create_widgets(self):
        # Заголовок
        ctk.CTkLabel(self.root, text="YouTube Downloader", 
                    font=ctk.CTkFont(size=26, weight="bold")).pack(pady=20)

        # URL
        ctk.CTkLabel(self.root, text="Посилання на відео або плейлист:").pack(anchor="w", padx=40)
        ctk.CTkEntry(self.root, textvariable=self.url_var, width=680, height=40,
                    font=ctk.CTkFont(size=14)).pack(pady=10, padx=40)

        # Папка збереження
        path_frame = ctk.CTkFrame(self.root)
        path_frame.pack(pady=10, padx=40, fill="x")
        ctk.CTkLabel(path_frame, text="Папка збереження:").pack(side="left", padx=10)
        self.path_label = ctk.CTkLabel(path_frame, text=self.save_path, anchor="w")
        self.path_label.pack(side="left", fill="x", expand=True, padx=10)
        ctk.CTkButton(path_frame, text="Обрати папку", width=140,
                     command=self.choose_directory).pack(side="right", padx=10)

        # === Вибір якості та формату ===
        options_frame = ctk.CTkFrame(self.root)
        options_frame.pack(pady=15, padx=40, fill="x")

        ctk.CTkLabel(options_frame, text="Якість відео:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(10,5))

        self.quality_var = ctk.StringVar(value="1080")
        qualities = [
            ("720p", "720"),
            ("1080p (Full HD)", "1080"),
            ("1440p (2K)", "1440"),
            ("2160p (4K)", "2160")
        ]

        for text, value in qualities:
            ctk.CTkRadioButton(options_frame, text=text, variable=self.quality_var, 
                              value=value).pack(anchor="w", padx=40, pady=3)

        # Вибір формату контейнера
        ctk.CTkLabel(options_frame, text="Формат файлу:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(15,5))

        self.container_var = ctk.StringVar(value="mp4")
        ctk.CTkRadioButton(options_frame, text="MP4 (найкраща сумісність)", 
                          variable=self.container_var, value="mp4").pack(anchor="w", padx=40, pady=3)
        ctk.CTkRadioButton(options_frame, text="MKV (максимальна якість)", 
                          variable=self.container_var, value="mkv").pack(anchor="w", padx=40, pady=3)

        # Тип завантаження (відео або тільки аудіо)
        ctk.CTkLabel(options_frame, text="Тип завантаження:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(15,5))
        
        self.download_type = ctk.StringVar(value="video")
        ctk.CTkRadioButton(options_frame, text="Відео + аудіо", 
                          variable=self.download_type, value="video").pack(anchor="w", padx=40, pady=3)
        ctk.CTkRadioButton(options_frame, text="Тільки аудіо (MP3)", 
                          variable=self.download_type, value="audio").pack(anchor="w", padx=40, pady=3)

        # Кнопка завантаження
        self.download_btn = ctk.CTkButton(self.root, text="Завантажити", height=55,
                                         font=ctk.CTkFont(size=18, weight="bold"),
                                         command=self.start_download)
        self.download_btn.pack(pady=30)

        # Прогрес-бар
        self.progress = ctk.CTkProgressBar(self.root, width=680, height=22)
        self.progress.pack(pady=10, padx=40)
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(self.root, text="Готово до роботи", text_color="lightgray")
        self.status_label.pack(pady=8)

    def choose_directory(self):
        folder = filedialog.askdirectory(initialdir=self.save_path)
        if folder:
            self.save_path = folder
            self.path_label.configure(text=self.save_path)

    def start_download(self):
        if not self.url_var.get().strip():
            messagebox.showwarning("Помилка", "Введіть посилання!")
            return

        if self.is_downloading:
            return

        self.is_downloading = True
        self.download_btn.configure(state="disabled", text="Завантаження...")
        self.progress.set(0)
        self.status_label.configure(text="Підготовка...", text_color="lightgray")

        threading.Thread(target=self.download_video, daemon=True).start()

    def download_video(self):
        url = self.url_var.get().strip()
        quality = self.quality_var.get()
        container = self.container_var.get()

        ydl_opts = {
            'outtmpl': os.path.join(self.save_path, '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'quiet': False,
        }

        if self.download_type.get() == "audio":
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            # Вибір якості
            if quality == "2160":
                format_str = f"bestvideo[height<=2160]+bestaudio/best[height<=2160]"
            elif quality == "1440":
                format_str = f"bestvideo[height<=1440]+bestaudio/best[height<=1440]"
            elif quality == "1080":
                format_str = f"bestvideo[height<=1080]+bestaudio/best[height<=1080]"
            else:  # 720p
                format_str = f"bestvideo[height<=720]+bestaudio/best[height<=720]"

            ydl_opts.update({
                'format': format_str,
                'merge_output_format': container,   # mp4 або mkv
            })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.status_label.configure(text="Отримання інформації про відео...")
                ydl.download([url])

            self.status_label.configure(text=f"✅ Готово! Збережено як .{container}", text_color="green")
            messagebox.showinfo("Успіх", f"Завантаження завершено!\nФормат: {container.upper()}")

        except Exception as e:
            self.status_label.configure(text=f"Помилка: {str(e)[:70]}...", text_color="red")
            messagebox.showerror("Помилка", f"Не вдалося завантажити:\n{str(e)}")

        finally:
            self.is_downloading = False
            self.download_btn.configure(state="normal", text="Завантажити")
            self.progress.set(0)

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                percent = d.get('_percent_str', '0%').strip()
                self.status_label.configure(text=f"Завантаження: {percent}")
                if 'total_bytes' in d and d['total_bytes'] > 0:
                    self.progress.set(d['downloaded_bytes'] / d['total_bytes'])
            except:
                pass
        elif d['status'] == 'finished':
            self.status_label.configure(text="Обробка файлу через ffmpeg...")

    def run(self):
        self.root.mainloop()


# Запуск
if __name__ == "__main__":
    app = YouTubeDownloader()
    app.run()