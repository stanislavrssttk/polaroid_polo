import random
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QMessageBox,
    QSlider,
)

from ui.freq_visualizer import FreqVisualizer
from core.game import Game
from core.audio_engine import AudioEngine
from core.utils import find_audio_files, is_audio_file


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Freq Trainer")
        self.resize(1200, 700)

        self.game = Game()
        self.audio = AudioEngine()
        self._round_active = False

        self.mode = "sandbox"  # "sandbox" | "story"

        self.story_level = 1
        self.story_levels_total = 5
        self.story_level_complete = False
        self.story_finished = False

        # dB диапазон по уровням: L1..L5
        self.story_gain_abs_by_level = [12.0, 9.0, 6.0, 3.0, 1.5]

        # N очков за ОДИН ответ, чтобы пройти уровень (L1..L5) — меняй вручную
        self.story_pass_gained_by_level = [60, 60, 60, 60, 60]

        # папка с треками сюжетки (рядом с app.py)
        self.story_folder = str(Path(__file__).resolve().parents[1] / "songs_story")

        self._last_selected_gain_db: float | None = None
        self._last_hover_gain_db: float | None = None

        self._last_hover_freq: float | None = None
        self._last_selected_freq: float | None = None

        self.song_files: list[str] = []
        self.current_song_path: str | None = None

        self._true_gain_db: float | None = None
        self._true_q: float | None = None

        self._init_ui()
        self._apply_styles()
        self._connect_signals()

    # ── UI ──────────────────────────────────────────────────────────

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        self.score_label = QLabel("SCORE: 0")
        self.combo_label = QLabel("COMBO: x1.0")

        self.settings_button = QPushButton("Settings")
        self.mode_button = QPushButton("Mode: Sandbox")
        self.story_label = QLabel("")

        top_bar.addWidget(self.story_label)
        top_bar.addWidget(self.mode_button)
        top_bar.addStretch(1)
        top_bar.addWidget(self.score_label)
        top_bar.addWidget(self.combo_label)
        top_bar.addStretch(1)
        top_bar.addWidget(self.settings_button)

        main_layout.addLayout(top_bar)

        self.info_label = QLabel("Выберите папку или файл с треками, чтобы начать.")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setWordWrap(True)
        main_layout.addWidget(self.info_label)

        center_layout = QVBoxLayout()
        center_layout.setSpacing(8)

        self.freq_display = QLabel("Freq: — Hz")
        self.freq_display.setAlignment(Qt.AlignCenter)
        self.freq_display.setFixedHeight(32)

        self.visualizer = FreqVisualizer()
        center_layout.addWidget(self.freq_display)
        center_layout.addWidget(self.visualizer)

        main_layout.addLayout(center_layout, stretch=1)

        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)

        self.new_round_button = QPushButton("New Round")
        self.play_button = QPushButton("Play")
        self.ab_button = QPushButton("A / B")
        self.load_folder_button = QPushButton("Load Folder...")
        self.load_file_button = QPushButton("Load File...")

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(120)

        self.play_button.setEnabled(False)

        bottom_bar.addWidget(self.new_round_button)
        bottom_bar.addWidget(self.play_button)
        bottom_bar.addWidget(self.volume_slider)
        bottom_bar.addWidget(self.ab_button)
        bottom_bar.addStretch(1)
        bottom_bar.addWidget(self.load_folder_button)
        bottom_bar.addWidget(self.load_file_button)

        main_layout.addLayout(bottom_bar)

    def _apply_styles(self):
        self.setStyleSheet("""
        QMainWindow { background-color: #111218; }
        QLabel { color: #FFFFFF; }
        QPushButton {
            background: #30343F;
            color: white;
            border-radius: 8px;
            padding: 8px 14px;
            font-weight: bold;
        }
        QPushButton:hover { background: #3C4250; }
        QPushButton:pressed { background: #1E2129; }
        QPushButton:disabled {
            background: #222222;
            color: #777777;
        }
        """)

    def _connect_signals(self):
        self.visualizer.frequencyHovered.connect(self._on_frequency_hovered)
        self.visualizer.frequencySelected.connect(self._on_frequency_selected)
        self.mode_button.clicked.connect(self._on_mode_clicked)

        self.new_round_button.clicked.connect(self._on_new_round_clicked)
        self.play_button.clicked.connect(self._on_play_clicked)
        self.ab_button.clicked.connect(self._on_ab_clicked)
        self.load_folder_button.clicked.connect(self._on_load_folder_clicked)
        self.load_file_button.clicked.connect(self._on_load_file_clicked)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)

    # ── handlers ────────────────────────────────────────────────────

    def _on_volume_changed(self, value: int):
        self.audio.set_volume(value / 100.0)

    def _on_frequency_hovered(self, freq: float, gain_db: float):
        self._last_hover_freq = freq
        self._last_hover_gain_db = gain_db
        self.freq_display.setText(
            f"Freq: {freq:,.0f} Hz | Gain: {gain_db:+.1f} dB (range: ±15 dB)".replace(",", " ")
        )

    def _on_frequency_selected(self, freq: float, gain_db: float):
        if not self._round_active:
            return
        self._last_selected_freq = freq
        self._last_selected_gain_db = gain_db
        self._confirm_answer()

    def _on_new_round_clicked(self):
        if self.mode == "story":
            if self.story_finished:
                # уже победа — просто остаёмся в Sandbox
                return

            if self.story_level_complete:
                if self.story_level < self.story_levels_total:
                    self.story_level += 1
                self.story_level_complete = False

                self.game.reset()
                self.score_label.setText("SCORE: 0")
                self.combo_label.setText("COMBO: x1.0")
                self._update_story_label()

        self._start_new_round()

    def _on_play_clicked(self):
        if not self._ensure_song_available():
            return

        if not self._round_active:
            self.info_label.setText("Музыку можно включить только во время раунда.")
            return

        self.audio.toggle_play()
        self._update_play_button()

    def _on_ab_clicked(self):
        self.audio.toggle_ab()
        mode = "ORIG" if self.audio.is_ab_original else "EQ"
        self.info_label.setText(f"A/B mode: {mode} | трек: {self._short_song_name()}")

    def _on_load_folder_clicked(self):
        if self.mode == "story":
            return

        folder = QFileDialog.getExistingDirectory(self, "Выбор папки с треками")
        if not folder:
            return

        files = find_audio_files(folder)
        if not files:
            QMessageBox.information(self, "Freq Trainer", "В этой папке нет аудиофайлов.")
            return

        self.song_files = files
        self.current_song_path = None
        self.play_button.setEnabled(True)

        self.info_label.setText(f"Загружено {len(files)} файлов. Запускаю раунд...")
        self._start_new_round()

    def _on_load_file_clicked(self):
        if self.mode == "story":
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбор аудиофайла",
            "",
            "Audio files (*.wav *.flac *.mp3 *.ogg *.aiff *.aif);;All files (*.*)",
        )
        if not path:
            return

        if not is_audio_file(path):
            QMessageBox.warning(self, "Freq Trainer", "Это не поддерживаемый аудиофайл.")
            return

        self.song_files = []
        self.current_song_path = path
        self.play_button.setEnabled(True)

        self.info_label.setText(f"Загружен файл: {self._short_song_name()}. Запускаю раунд...")
        self._start_new_round()

    # ── helpers ─────────────────────────────────────────────────────

    def _ensure_song_available(self) -> bool:
        if self.song_files or self.current_song_path:
            return True
        self.info_label.setText("Нет файлов для воспроизведения. Загрузите папку или файл.")
        return False

    def _short_song_name(self) -> str:
        if not self.current_song_path:
            return "—"
        return Path(self.current_song_path).name

    def _start_new_round(self):
        if not self._ensure_song_available():
            return

        self.audio.stop()
        self._update_play_button()

        if self.song_files:
            self.current_song_path = random.choice(self.song_files)

        if self.current_song_path:
            try:
                self.audio.load_file(self.current_song_path)
            except Exception as e:
                self.info_label.setText(f"Ошибка загрузки файла: {e}")
                return

        if self.mode == "story":
            g = self.story_gain_abs_by_level[self.story_level - 1]
            true_freq, true_gain_db = self.game.new_round(-g, g)
        else:
            true_freq, true_gain_db = self.game.new_round(-15.0, 15.0)

        print(f"[DEBUG] TRUE freq={true_freq:.2f} Hz | TRUE gain={true_gain_db:+.2f} dB | mode={self.mode}")

        q = random.uniform(0.8, 2.0)

        self._true_gain_db = true_gain_db
        self._true_q = q

        self.audio.is_ab_original = False
        self.audio.set_peaking_eq(true_freq, q=q, gain_db=true_gain_db)

        self._last_selected_freq = None
        self._last_selected_gain_db = None

        self._round_active = True
        self.play_button.setEnabled(True)

        if self.mode == "story":
            target = self.story_pass_gained_by_level[self.story_level - 1]
            self.info_label.setText(
                f"Story L{self.story_level}/{self.story_levels_total} | нужно за один ответ: +{target} pts\n"
                f"Трек: {self._short_song_name()} | выбери freq+gain и кликни по полосе."
            )
        else:
            self.info_label.setText(
                f"Трек: {self._short_song_name()} | выбери freq+gain и кликни по полосе."
            )

    def _confirm_answer(self):
        if self.game.current_freq is None:
            self.info_label.setText("Сначала начни раунд (New Round).")
            return

        guess_f = self._last_selected_freq or self._last_hover_freq
        guess_g = self._last_selected_gain_db
        if guess_g is None:
            guess_g = self._last_hover_gain_db

        if guess_f is None or guess_g is None:
            self.info_label.setText("Сначала выбери freq+gain (наведи и кликни).")
            return

        result = self.game.submit_answer(guess_f, guess_g)

        self.audio.stop()
        self._update_play_button()
        self.play_button.setEnabled(False)
        self._round_active = False

        self.score_label.setText(f"SCORE: {result.total_score}")
        self.combo_label.setText(f"COMBO: x{result.multiplier:.1f}")

        self.info_label.setText(
            (
                f"RESULT | +{result.gained} pts  →  TOTAL {result.total_score} pts  |  COMBO x{result.multiplier:.1f}\n"
                f"Freq: true {result.true_freq:,.0f} Hz  |  you {result.guessed_freq:,.0f} Hz  |  err {abs(result.err_cents):.0f} cents\n"
                f"Gain: true {result.true_gain_db:+.1f} dB  |  you {result.guessed_gain_db:+.1f} dB  |  err {abs(result.err_gain_db):.1f} dB"
            ).replace(",", " ")
        )

        if self.mode == "story":
            target = self.story_pass_gained_by_level[self.story_level - 1]

            if result.gained >= target:
                if self.story_level >= self.story_levels_total:
                    self.story_level_complete = True
                    self.story_finished = True

                    self.info_label.setText(
                        self.info_label.text()
                        + "\n\nПоздравляем! phashion kiwi\nПереключаю на Sandbox."
                    )
                    self._switch_to_sandbox()
                else:
                    self.story_level_complete = True
                    self.info_label.setText(
                        self.info_label.text()
                        + f"\n\nУровень пройден! (+{result.gained} >= {target}) Нажми New Round, чтобы начать уровень {self.story_level + 1}."
                    )
            else:
                self.story_level_complete = False
                self.info_label.setText(
                    self.info_label.text()
                    + f"\n\nУровень НЕ пройден. Нужно за один ответ: минимум {target} pts (у тебя +{result.gained}). Нажми New Round и попробуй снова."
                )
        else:
            self.info_label.setText(self.info_label.text() + "\n\nНажми New Round, чтобы продолжить.")

    def _update_play_button(self):
        self.play_button.setText("Stop" if self.audio.is_playing else "Play")

    # ── Mode switching ───────────────────────────────────────────────

    def _on_mode_clicked(self):
        if getattr(self, "mode", "sandbox") == "sandbox":
            self._switch_to_story()
        else:
            self._switch_to_sandbox()

    def _switch_to_story(self):
        self.mode = "story"
        self.mode_button.setText("Mode: Story")

        self.story_level = 1
        self.story_level_complete = False
        self.story_finished = False

        self.game.reset()
        self.score_label.setText("SCORE: 0")
        self.combo_label.setText("COMBO: x1.0")

        self.song_files = find_audio_files(self.story_folder)
        self.current_song_path = None

        self.load_folder_button.hide()
        self.load_file_button.hide()

        if not self.song_files:
            self.play_button.setEnabled(False)
            self.info_label.setText(
                f"Сюжетка: нет треков в папке {self.story_folder}. Добавь файлы и перезапусти."
            )
            self._update_story_label()
            return

        self.play_button.setEnabled(True)
        self._update_story_label()
        self._start_new_round()

    def _switch_to_sandbox(self):
        self.mode = "sandbox"
        self.mode_button.setText("Mode: Sandbox")

        self.story_label.setText("")
        self.story_level_complete = False
        self.story_finished = False

        self.load_folder_button.show()
        self.load_file_button.show()

        self.info_label.setText("Песочница: загрузите папку или файл с треками.")
        # в sandbox не стартуем автоматически — как ты и хотел ранее

    def _update_story_label(self):
        if self.mode != "story":
            self.story_label.setText("")
            return
        target = self.story_pass_gained_by_level[self.story_level - 1]
        g = self.story_gain_abs_by_level[self.story_level - 1]
        self.story_label.setText(
            f"Story: L{self.story_level}/{self.story_levels_total} | need +{target} | gain ±{g:g}dB"
        )
