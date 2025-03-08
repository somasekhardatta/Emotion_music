import cv2
import numpy as np
import os
import random
import json
import logging
from PyQt5.QtWidgets import (
    QApplication, QLabel, QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QSlider, QStyle, QMessageBox, QTextEdit, QLineEdit, QDialog, QComboBox, QTabWidget, QListWidget, QAction, QMenuBar, QTableWidget, QTableWidgetItem, QHeaderView, QMainWindow, QToolBar
)
from PyQt5.QtGui import QImage, QPixmap, QPalette, QBrush, QFont, QIcon
from PyQt5.QtCore import QTimer, Qt, QUrl, QDateTime, QTime
from keras.models import load_model
from keras.preprocessing.image import img_to_array
import vlc  # Use VLC for media playback

# Set up logging
logging.basicConfig(filename="app.log", level=logging.ERROR)

# Load pre-trained emotion detection model
model_path = "emotion_model.h5"
if not os.path.exists(model_path):
    logging.error(f"Model file '{model_path}' not found!")
    exit()
model = load_model(model_path)

# Path to the folder containing emotion subfolders
music_folder = os.path.join("Emotion_music")
if not os.path.exists(music_folder):
    logging.error(f"Music folder '{music_folder}' not found!")
    exit()

# Emotion labels
emotion_labels = ['Angry', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']

# Read songs from folders
emotion_songs = {}
for emotion in emotion_labels:
    emotion_folder = os.path.join(music_folder, emotion)
    if os.path.exists(emotion_folder):
        emotion_songs[emotion] = {
            "Telugu": [
                os.path.join(emotion_folder, "Telugu", song)
                for song in os.listdir(os.path.join(emotion_folder, "Telugu"))
                if song.endswith(".mp3")
            ],
            "Tamil": [
                os.path.join(emotion_folder, "Tamil", song)
                for song in os.listdir(os.path.join(emotion_folder, "Tamil"))
                if song.endswith(".mp3")
            ],
            "English": [
                os.path.join(emotion_folder, "English", song)
                for song in os.listdir(os.path.join(emotion_folder, "English"))
                if song.endswith(".mp3")
            ],
        }
    else:
        emotion_songs[emotion] = {"Telugu": [], "Tamil": [], "English": []}

# File to store user history
history_file = "history.json"

class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.setGeometry(200, 200, 300, 150)
        
        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("Enter your username")
        
        self.login_button = QPushButton("Login", self)
        self.login_button.clicked.connect(self.login)
        
        layout = QVBoxLayout()
        layout.addWidget(self.username_input)
        layout.addWidget(self.login_button)
        self.setLayout(layout)
    
    def login(self):
        self.username = self.username_input.text().strip()
        if self.username:
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Username cannot be empty!")

class EmotionMusicApp(QMainWindow):  # Changed from QWidget to QMainWindow
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Emotion-Based Music Player")
        self.setGeometry(100, 100, 1000, 800)

        # Set background image
        self.set_background("wallpaperflare.com_wallpaper.jpg")
        
        # Create a central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Add a logout button to the toolbar
        self.add_logout_button()
        
        # Create tabs
        self.tabs = QTabWidget()
        
        # Tab 1: Emotion Detection
        detection_tab = QWidget()
        detection_layout = QVBoxLayout()
        
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignCenter)
        
        self.emotion_label = QLabel("Detecting Emotion...", self)
        self.emotion_label.setAlignment(Qt.AlignCenter)
        self.emotion_label.setFont(QFont("Arial", 16))
        
        self.detection_button = QPushButton("Start Detection", self)
        self.detection_button.clicked.connect(self.toggle_webcam)
        
        detection_layout.addWidget(self.video_label)
        detection_layout.addWidget(self.emotion_label)
        detection_layout.addWidget(self.detection_button)
        detection_tab.setLayout(detection_layout)
        
        # Tab 2: Music Player
        player_tab = QWidget()
        player_layout = QVBoxLayout()
        
        # Language Selection
        language_layout = QHBoxLayout()
        self.language_label = QLabel("Select Language:", self)
        self.language_label.setFont(QFont("Arial", 14))
        self.language_combo = QComboBox(self)
        self.language_combo.addItems(["Telugu", "Tamil", "English"])
        self.language_combo.setCurrentIndex(2)  # Default to English
        self.language_combo.currentTextChanged.connect(self.update_song_list)
        language_layout.addWidget(self.language_label)
        language_layout.addWidget(self.language_combo)
        
        # Song List
        self.song_list_label = QLabel("Available Songs:", self)
        self.song_list_label.setFont(QFont("Arial", 14))
        self.song_list = QListWidget(self)
        self.song_list.itemDoubleClicked.connect(self.play_selected_song)
        
        # Player Controls
        control_layout = QHBoxLayout()
        self.play_button = QPushButton(self)
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_button.clicked.connect(self.play_music)
        self.play_button.setToolTip("Play the current song")
        
        self.pause_button = QPushButton(self)
        self.pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self.pause_button.clicked.connect(self.pause_music)
        self.pause_button.setToolTip("Pause the current song")
        
        self.stop_button = QPushButton(self)
        self.stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stop_button.clicked.connect(self.stop_music)
        self.stop_button.setToolTip("Stop the current song")
        
        self.next_button = QPushButton(self)
        self.next_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipForward))
        self.next_button.clicked.connect(self.next_song)
        self.next_button.setToolTip("Play the next song")
        
        self.prev_button = QPushButton(self)
        self.prev_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipBackward))
        self.prev_button.clicked.connect(self.prev_song)
        self.prev_button.setToolTip("Play the previous song")
        
        self.shuffle_button = QPushButton("Shuffle", self)
        self.shuffle_button.clicked.connect(self.shuffle_songs)
        self.shuffle_button.setToolTip("Shuffle the playlist")
        
        self.repeat_button = QPushButton("Repeat: Off", self)
        self.repeat_button.clicked.connect(self.toggle_repeat_mode)
        self.repeat_button.setToolTip("Toggle repeat mode")
        
        control_layout.addWidget(self.prev_button)
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.next_button)
        control_layout.addWidget(self.shuffle_button)
        control_layout.addWidget(self.repeat_button)
        
        # Volume and Progress
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("Volume:"))
        self.volume_slider = QSlider(Qt.Horizontal, self)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.valueChanged.connect(self.set_volume)
        volume_layout.addWidget(self.volume_slider)
        
        self.progress_slider = QSlider(Qt.Horizontal, self)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.sliderMoved.connect(self.set_position)
        
        self.song_label = QLabel("No Song Playing", self)
        self.song_label.setAlignment(Qt.AlignCenter)
        
        self.progress_label = QLabel("00:00 / 00:00", self)
        self.progress_label.setAlignment(Qt.AlignCenter)
        
        player_layout.addLayout(language_layout)
        player_layout.addWidget(self.song_list_label)
        player_layout.addWidget(self.song_list)
        player_layout.addLayout(control_layout)
        player_layout.addWidget(self.progress_slider)
        player_layout.addWidget(self.progress_label)
        player_layout.addWidget(self.song_label)
        player_layout.addLayout(volume_layout)
        player_tab.setLayout(player_layout)
        
        # Tab 3: History
        history_tab = QWidget()
        history_layout = QVBoxLayout()
        
        self.history_label = QLabel("Player History:", self)
        self.history_label.setFont(QFont("Arial", 14))
        
        # Create a QTableWidget for history
        self.history_table = QTableWidget(self)
        self.history_table.setColumnCount(3)  # Three columns: Timestamp, Emotion, Language
        self.history_table.setHorizontalHeaderLabels(["Timestamp", "Emotion", "Language"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)  # Stretch columns to fit
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)  # Make the table read-only
        
        # Style the table
        self.history_table.setStyleSheet("""
            QTableWidget {
                background-color: #2E3440;
                color: white;
                font-weight: bold;
                border: 1px solid purple;
                border-radius: 5px;
            }
            QHeaderView::section {
                background-color: purple;
                color: white;
                font-weight: bold;
                padding: 10px;
            }
            QTableWidget::item {
                padding: 10px;
            }
        """)
        
        self.clear_history_button = QPushButton("Clear History", self)
        self.clear_history_button.clicked.connect(self.clear_history)
        
        history_layout.addWidget(self.history_label)
        history_layout.addWidget(self.history_table)
        history_layout.addWidget(self.clear_history_button)
        history_tab.setLayout(history_layout)
        
        # Add tabs to the tab widget
        self.tabs.addTab(detection_tab, "Emotion Detection")
        self.tabs.addTab(player_tab, "Music Player")
        self.tabs.addTab(history_tab, "Player History")
        
        # Add tabs to the main layout
        main_layout.addWidget(self.tabs)
        
        # Initialize VLC media player
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        
        # Timer for updating frames
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.capture = None  # Webcam capture instance
        self.detected_emotion = None  # Track the detected emotion
        self.capture_duration = 10000  # Stop after 10 seconds
        self.detection_timer = QTimer()
        self.detection_timer.timeout.connect(self.stop_webcam)
        self.frame_counter = 0
        self.webcam_active = False  # Track webcam state
        self.username = None  # Track the logged-in user
        self.history = self.load_history()  # Load history from file
        self.shuffle_mode = False  # Track shuffle mode
        self.repeat_mode = False  # Track repeat mode
        
        # Timer for updating the progress slider
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_progress)
        
        # Initialize song list
        self.current_song_index = 0
        self.update_song_list()
    
    def add_logout_button(self):
        """Add a logout button to the top-right corner."""
        logout_action = QAction("Logout", self)
        logout_action.triggered.connect(self.logout)
        
        toolbar = QToolBar("Toolbar")
        toolbar.addAction(logout_action)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
    
    def logout(self):
        """Log out the user and reset the application."""
        # Stop music playback
        self.stop_music()
        
        # Stop webcam if active
        if self.capture:
            self.stop_webcam()
        
        # Clear user data
        self.username = None
        self.history = {}
        self.history_table.setRowCount(0)
        
        # Hide the main window
        self.hide()
        
        # Show the login window
        self.login_window = LoginWindow()
        if self.login_window.exec_() == QDialog.Accepted:
            self.username = self.login_window.username
            self.show()
    
    def set_background(self, image_path):
        """Set the background image or fallback to a solid color."""
        if os.path.exists(image_path):
            palette = QPalette()
            palette.setBrush(QPalette.Background, QBrush(QPixmap(image_path)))
            self.setPalette(palette)
        else:
            self.setStyleSheet("background-color: #2E3440;")  # Fallback color
    
    def toggle_webcam(self):
        if self.capture is None:
            # Start webcam
            self.capture = cv2.VideoCapture(0)
            if not self.capture.isOpened():
                QMessageBox.critical(self, "Error", "Webcam not accessible!")
                return
            self.timer.start(100)
            self.detection_timer.start(self.capture_duration)
            self.detection_button.setText("Stop Detection")
            self.webcam_active = True
            self.emotion_label.setText("Detecting Emotion...")
        else:
            # Stop webcam
            self.stop_webcam()
    
    def stop_webcam(self):
        self.timer.stop()
        self.detection_timer.stop()
        if self.capture:
            self.capture.release()
        self.capture = None
        self.detection_button.setText("Start Detection")
        self.webcam_active = False
        
        # Play music after webcam is turned off
        if self.detected_emotion:
            self.play_music()
            self.update_history()  # Update player history
            
            # Automatically switch to the Music Player tab
            self.tabs.setCurrentIndex(1)  # Index 1 is the Music Player tab
    
    def update_frame(self):
        if self.capture is None:
            return

        ret, frame = self.capture.read()
        if ret:
            self.frame_counter += 1
            if self.frame_counter % 5 == 0:  # Detect emotion every 5 frames
                self.detect_emotion(frame)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channel = frame.shape
            bytes_per_line = channel * width
            qimg = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            self.video_label.setPixmap(QPixmap.fromImage(qimg))
    
    def detect_emotion(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        if face_cascade.empty():
            QMessageBox.critical(self, "Error", "Haar Cascade file not found!")
            return
        
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
        
        if len(faces) == 0:
            self.emotion_label.setText("No Face Detected")
            return
        
        for (x, y, w, h) in faces:
            # Draw a rectangle around the detected face
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            face = gray[y:y + h, x:x + w]
            face = cv2.resize(face, (48, 48))
            face = img_to_array(face)
            face = np.expand_dims(face, axis=0)
            face /= 255.0
            preds = model.predict(face)[0]
            self.detected_emotion = emotion_labels[np.argmax(preds)]
            self.emotion_label.setText(f"Detected Emotion: {self.detected_emotion}")
            self.update_song_list()
    
    def update_song_list(self):
        """Update the song list based on the detected emotion and selected language."""
        if self.detected_emotion:
            selected_language = self.language_combo.currentText()
            songs = emotion_songs[self.detected_emotion][selected_language]
            self.song_list.clear()
            for song in songs:
                self.song_list.addItem(os.path.basename(song))
            # Reset current song index
            self.current_song_index = 0
    
    def play_selected_song(self, item):
        """Play the selected song from the list."""
        selected_language = self.language_combo.currentText()
        songs = emotion_songs[self.detected_emotion][selected_language]
        if songs:
            song_path = songs[self.song_list.row(item)]
            media = self.instance.media_new(song_path)
            self.player.set_media(media)
            self.player.play()
            self.song_label.setText(f"Playing: {os.path.basename(song_path)}")
            
            # Start the progress timer
            self.progress_timer.start(1000)  # Update every second
    
    def update_progress(self):
        """Update the progress slider and labels."""
        if self.player.is_playing():
            # Get the total duration of the song in milliseconds
            total_time = self.player.get_length()
            if total_time > 0:
                # Get the current playback position in milliseconds
                current_time = self.player.get_time()

                # Convert milliseconds to minutes and seconds
                total_time_str = QTime(0, 0).addMSecs(total_time).toString("mm:ss")
                current_time_str = QTime(0, 0).addMSecs(current_time).toString("mm:ss")

                # Update the progress label
                self.progress_label.setText(f"{current_time_str} / {total_time_str}")

                # Update the progress slider
                self.progress_slider.setMaximum(total_time)
                self.progress_slider.setValue(current_time)
    
    def set_position(self, position):
        """Set the playback position of the current song."""
        if self.player.get_media():
            # Set the player's position based on the slider value
            self.player.set_time(position)
            self.update_progress()  # Update the UI immediately
    
    def play_music(self):
        if self.detected_emotion:
            selected_language = self.language_combo.currentText()
            songs = emotion_songs[self.detected_emotion][selected_language]
            if songs:
                if self.shuffle_mode:
                    song_path = random.choice(songs)
                else:
                    self.current_song_index = self.current_song_index % len(songs)
                    song_path = songs[self.current_song_index]
                media = self.instance.media_new(song_path)
                self.player.set_media(media)
                self.player.play()
                self.song_label.setText(f"Playing: {os.path.basename(song_path)}")
                
                # Start the progress timer
                self.progress_timer.start(1000)  # Update every second
            else:
                self.song_label.setText(f"No {selected_language} songs available for this emotion.")
        else:
            self.song_label.setText("No songs available for this emotion.")
    
    def pause_music(self):
        self.player.pause()
    
    def stop_music(self):
        self.player.stop()
        self.song_label.setText("Playback Stopped")
        
        # Stop the progress timer
        self.progress_timer.stop()
        
        # Reset the progress slider and label
        self.progress_slider.setValue(0)
        self.progress_label.setText("00:00 / 00:00")
    
    def next_song(self):
        if self.detected_emotion:
            selected_language = self.language_combo.currentText()
            songs = emotion_songs[self.detected_emotion][selected_language]
            if songs:
                self.current_song_index = (self.current_song_index + 1) % len(songs)
                self.play_music()
    
    def prev_song(self):
        if self.detected_emotion:
            selected_language = self.language_combo.currentText()
            songs = emotion_songs[self.detected_emotion][selected_language]
            if songs:
                self.current_song_index = (self.current_song_index - 1) % len(songs)
                self.play_music()
    
    def shuffle_songs(self):
        self.shuffle_mode = not self.shuffle_mode
        if self.shuffle_mode:
            self.shuffle_button.setStyleSheet("background-color: #6A0DAD;")
        else:
            self.shuffle_button.setStyleSheet("background-color: purple;")
        self.play_music()
    
    def toggle_repeat_mode(self):
        self.repeat_mode = not self.repeat_mode
        if self.repeat_mode:
            self.repeat_button.setText("Repeat: On")
        else:
            self.repeat_button.setText("Repeat: Off")
    
    def set_volume(self, value):
        self.player.audio_set_volume(value)
    
    def update_history(self):
        """Update the player history with the detected emotion and timestamp."""
        if self.username:
            timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
            emotion = self.detected_emotion
            language = self.language_combo.currentText()
            
            # Create a history entry as a list of strings
            history_entry = [timestamp, emotion, language]
            
            # Add entry to the user's history
            if self.username not in self.history:
                self.history[self.username] = []
            self.history[self.username].append(history_entry)
            
            # Update the history table
            self.update_history_table()
    
    def update_history_table(self):
        """Update the history table with the latest entries."""
        self.history_table.setRowCount(0)  # Clear the table
        if self.username in self.history:
            for entry in self.history[self.username]:
                row_position = self.history_table.rowCount()
                self.history_table.insertRow(row_position)
                for col, data in enumerate(entry):
                    item = QTableWidgetItem(data)
                    self.history_table.setItem(row_position, col, item)
    
    def clear_history(self):
        """Clear the history for the current user."""
        if self.username in self.history:
            self.history[self.username] = []
            self.history_table.setRowCount(0)  # Clear the table
            self.save_history()
    
    def load_history(self):
        """Load history from a file."""
        if os.path.exists(history_file):
            with open(history_file, "r") as file:
                return json.load(file)
        return {}
    
    def save_history(self):
        """Save history to a file."""
        with open(history_file, "w") as file:
            json.dump(self.history, file)
    
    def closeEvent(self, event):
        """Save history when the application is closed."""
        self.save_history()
        event.accept()

if __name__ == "__main__":
    app = QApplication([])
    
    # Set global stylesheet for the application
    app.setStyleSheet("""
        QLabel, QPushButton {
            color: white;
            font-weight: bold;
        }
        QPushButton {
            background-color: purple;
            border-radius: 5px;
            padding: 10px;
        }
        QPushButton:hover {
            background-color: #6A0DAD;
        }
        QSlider::groove:horizontal {
            background: white;
            height: 8px;
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            background: purple;
            width: 18px;
            margin: -5px 0;
            border-radius: 9px;
        }
        QTextEdit {
            background-color: #2E3440;
            color: white;
            font-weight: bold;
            border: 1px solid purple;
            border-radius: 5px;
        }
        QComboBox {
            background-color: purple;
            color: white;
            font-weight: bold;
            border-radius: 5px;
            padding: 5px;
        }
        QTabWidget::pane {
            border: 2px solid purple;
            border-radius: 5px;
            padding: 10px;
        }
        QTabBar::tab {
            background-color: purple;
            color: white;
            font-weight: bold;
            padding: 10px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
        }
        QTabBar::tab:selected {
            background-color: #6A0DAD;
        }
        QListWidget {
            background-color: #2E3440;
            color: white;
            font-weight: bold;
            border: 1px solid purple;
            border-radius: 5px;
        }
    """)
    
    # Show login window
    login_window = LoginWindow()
    if login_window.exec_() == QDialog.Accepted:
        username = login_window.username
        window = EmotionMusicApp()
        window.username = username
        window.show()
        app.exec_()
