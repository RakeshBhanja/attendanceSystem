from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.popup import Popup

import cv2
import pandas as pd
from datetime import datetime

from attendance_core import AttendanceCore


class AttendanceUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.core = AttendanceCore()
        self.excel_path = None

        self.image = Image(size_hint=(1, 0.75))
        self.add_widget(self.image)

        self.status = Label(
            text="Select Excel file",
            size_hint=(1, 0.08)
        )
        self.add_widget(self.status)

        btns = BoxLayout(size_hint=(1, 0.12))
        btns.add_widget(Button(text="Select Excel", on_press=self.select_excel))
        btns.add_widget(Button(text="Start", on_press=self.start))
        btns.add_widget(Button(text="Stop", on_press=self.stop))
        self.add_widget(btns)

        self.capture = cv2.VideoCapture(0)

    # ---------------------------
    # FILE PICKER (FIXED)
    # ---------------------------
    def select_excel(self, instance):
        layout = BoxLayout(orientation="vertical")

        chooser = FileChooserIconView(
            filters=["*.xlsx"],
            path="."
        )

        confirm_btn = Button(
            text="Confirm Selection",
            size_hint=(1, 0.15)
        )

        layout.add_widget(chooser)
        layout.add_widget(confirm_btn)

        popup = Popup(
            title="Select Master Excel File",
            content=layout,
            size_hint=(0.9, 0.9)
        )

        def confirm(instance):
            if not chooser.selection:
                self.status.text = "❌ No file selected"
                return

            self.excel_path = chooser.selection[0]
            self.status.text = f"✔ Selected: {self.excel_path}"
            popup.dismiss()

        confirm_btn.bind(on_press=confirm)
        popup.open()

    # ---------------------------
    # START
    # ---------------------------
    def start(self, instance):
        if not self.excel_path:
            self.status.text = "❌ Select Excel first"
            return

        self.status.text = "Attendance Running..."
        Clock.schedule_interval(self.update, 1.0 / 15)

    # ---------------------------
    # STOP + SAVE
    # ---------------------------
    def stop(self, instance):
        Clock.unschedule(self.update)
        self.save_to_excel()
        self.core.finish()
        self.status.text = "✔ Attendance Saved"

    # ---------------------------
    # CAMERA UPDATE
    # ---------------------------
    def update(self, dt):
        ret, frame = self.capture.read()
        if not ret:
            return

        frame = self.core.process_frame(frame)

        buf = cv2.flip(frame, 0).tobytes()
        texture = Texture.create(
            size=(frame.shape[1], frame.shape[0]),
            colorfmt="bgr"
        )
        texture.blit_buffer(buf, colorfmt="bgr", bufferfmt="ubyte")
        self.image.texture = texture

    # ---------------------------
    # EXCEL UPDATE (ONCE)
    # ---------------------------
    def save_to_excel(self):
        master_df = pd.read_excel(self.excel_path)

        roll_col = master_df.columns[0]
        master_df[roll_col] = master_df[roll_col].astype(str)

        present_rolls = self.core.get_present_rolls()

        col_name = datetime.now().strftime("%Y-%m-%d_%H%M%S")

        master_df[col_name] = master_df[roll_col].apply(
            lambda r: "✔" if r in present_rolls else ""
        )

        

        master_df.to_excel(self.excel_path, index=False)


class AttendanceApp(App):
    def build(self):
        return AttendanceUI()


if __name__ == "__main__":
    AttendanceApp().run()
