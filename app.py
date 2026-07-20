import sys
from PySide6.QtWidgets import QApplication, QMainWindow

app = QApplication(sys.argv)

window = QMainWindow()
window.setWindowTitle("Stream Deck Macro")
window.resize(400, 400)
window.show()

sys.exit(app.exec())