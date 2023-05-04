"""CompCat V1.0, developed by Mervin van Brakel. Icon art by Roos ten Hoedt.
Extra thanks to Gilles Vink for the code reviews.
"""

import json
import ssl
import os
import urllib

import nuke
from PySide2 import QtCore, QtGui, QtWidgets

COMPCAT_FOLDER_PATH = os.path.dirname(os.path.realpath(__file__)).replace(os.sep, "/")


class CompCatWindow(QtWidgets.QMainWindow):
    """Main CompCat window with multi-threading.
    Note: Qt GUI cannot be updated from within a QThread,
    which is why there are several connected functions for
    handling the UI elements seperately.
    """

    def __init__(self, parent=None):
        """Initial window setup"""
        super().__init__()
        self.threadpool = QtCore.QThreadPool()

        self.loading_cat = False
        self.downloading_then_importing = False
        self.has_cat_stored = False
        self.currently_displaying_gif = False

        self.main_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.main_widget)
        self.setWindowTitle("CompCat")

        # Fixes a python SSL error that shows up a lot mainly on MacOS
        ssl._create_default_https_context = ssl._create_unverified_context

        self.create_user_interface()

        self.get_new_cat_image()

    def create_user_interface(self):
        """Creates the interface for the CompCat window."""
        self.layout = QtWidgets.QVBoxLayout()

        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)

        self.setFixedWidth(360)
        self.setFixedHeight(480)

        self.layout.addLayout(self._get_cat_creation_widgets())
        self.layout.addWidget(self._get_cat_displayer_widget())
        self.layout.addLayout(self._get_import_error_credits_widgets())

        self.main_widget.setLayout(self.layout)

    def _get_cat_creation_widgets(self):
        """Gets the image & gif buttons, size text and size slider."""
        self.cat_creation_layout = QtWidgets.QHBoxLayout()

        self.new_cat_button = QtWidgets.QPushButton("New image")
        self.new_cat_button.setToolTip(
            "Fetches a random new cat picture from the internet, yey!"
        )
        self.new_cat_button.clicked.connect(self.get_new_cat_image)
        self.cat_creation_layout.addWidget(self.new_cat_button, 1)

        self.new_gif_button = QtWidgets.QPushButton("New GIF")
        self.new_gif_button.setToolTip(
            "Fetches a random new cat gif from the internet, yey!"
        )
        self.new_gif_button.clicked.connect(self.get_new_cat_gif)
        self.cat_creation_layout.addWidget(self.new_gif_button, 1)

        self.size_text = QtWidgets.QLabel("Size: ")
        self.size_text.setFont(QtGui.QFont("Arial", 8))
        self.cat_creation_layout.addWidget(self.size_text)

        self.new_cat_size_slider = QtWidgets.QSlider()
        self.new_cat_size_slider.setOrientation(QtCore.Qt.Horizontal)
        self.new_cat_size_slider.setMinimum(300)
        self.new_cat_size_slider.setMaximum(1000)
        self.new_cat_size_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.new_cat_size_slider.setTickInterval(10)
        self.new_cat_size_slider.setValue(400)
        self.new_cat_size_slider.setToolTip(
            "Increase this slider to increase the size of the cat image."
        )
        self.cat_creation_layout.addWidget(self.new_cat_size_slider, 1)

        return self.cat_creation_layout

    def _get_cat_displayer_widget(self):
        """Gets the QLabel where cat images and GIFs will be displayed."""
        self.cat_image_label = QtWidgets.QLabel()
        self.loading_image = QtGui.QPixmap(f"{COMPCAT_FOLDER_PATH}/Loading.png")
        self.cat_image_label.setPixmap(self.loading_image)

        return self.cat_image_label

    def _get_import_error_credits_widgets(self):
        """Gets the import button, error displayer and credits."""
        self.import_error_credits_layout = QtWidgets.QVBoxLayout()

        self.import_button = QtWidgets.QPushButton("Import cat")
        self.import_button.setToolTip(
            "Imports the cat image as a read node and places it in the comp."
        )
        self.import_button.clicked.connect(self.import_cat)
        self.import_error_credits_layout.addWidget(self.import_button)

        self.error_displayer = QtWidgets.QLabel()
        self.error_displayer.setFont(QtGui.QFont("Arial", 10))
        self.error_displayer.setWordWrap(True)
        self.import_error_credits_layout.addWidget(self.error_displayer)

        self.credits = QtWidgets.QLabel(
            "CompCat V1.0 | A <a href=\"https://www.breaktools.info\" style=\"color: grey;\">BreakTool</a> by <a href=\"https://www.linkedin.com/in/mervin-van-brakel/\" style=\"color: grey;\">Mervin van Brakel</a>"
            )
        self.credits.setOpenExternalLinks(True)
        self.import_error_credits_layout.addWidget(self.credits)

        return self.import_error_credits_layout

    def get_new_cat_image(self):
        """Sets the correct variables for the cat worker function."""
        if not self.loading_cat:
            self.image_or_gif = "image"
            self.new_cat_button.setText("Loading...")
            self._get_new_cat_worker()

    def get_new_cat_gif(self):
        """Sets the correct variables for the cat worker function."""
        if not self.loading_cat:
            self.image_or_gif = "gif"
            self.new_gif_button.setText("Loading...")
            self._get_new_cat_worker()

    def _get_new_cat_worker(self):
        """Runs the cat get function on a seperate thread."""
        self.error_displayer.setText("")
        self.worker = Worker(self._get_new_cat)
        self.worker.signals.finished.connect(self._new_cat_loaded)
        self.threadpool.start(self.worker)
        self.loading_cat = True

    def _get_new_cat(self):
        """Main function that gets cat pictures using cataas.com.
        It first downloads a JSON file that represents a cat image,
        then uses that information for downloading the cat file.
        """
        try:
            if self.image_or_gif == "gif":
                self.cat_JSON = (
                    urllib.request.urlopen(
                        f"https://cataas.com/cat/gif?width={self.new_cat_size_slider.value()}&json=true"
                    )
                    .read()
                    .decode()
                )
            else:
                self.cat_JSON = (
                    urllib.request.urlopen(
                        f"https://cataas.com/cat?width={self.new_cat_size_slider.value()}&json=true"
                    )
                    .read()
                    .decode()
                )

            self.has_succesfully_connected = True

        except Exception as error:
            self.has_succesfully_connected = False
            self.error_message = error

        if self.has_succesfully_connected:
            self.cat_parsed_JSON = json.loads(self.cat_JSON)

            self.catDownload = urllib.request.urlopen(
                f"https://cataas.com{self.cat_parsed_JSON['url']}"
            )

            self.catDownloadRead = self.catDownload.read()
            self.has_cat_stored = True

    def _new_cat_loaded(self):
        """This function runs when the get cat function finishes. It is only for functions that update UI elements."""
        if not self.has_succesfully_connected:
            self.error_displayer.setText(
                f"CompCat couldn't connect with CATAAS.com... Error: {self.error_message}"
            )

            self.error_image = QtGui.QPixmap(f"{COMPCAT_FOLDER_PATH}/Error.png")
            self.cat_image_label.setPixmap(self.error_image)

        else:
            if self.image_or_gif == "gif":
                if self.currently_displaying_gif:
                    # Stop playing the GIF before changing it, otherwise Nuke will crash.
                    self.downloaded_cat_gif.stop()

                # Loads the GIF file as a QByteArray, stores it in a QBuffer and starts playing it as a QMovie.
                self.gif_byte_array = QtCore.QByteArray(self.catDownloadRead)
                self.gif_buffer = QtCore.QBuffer(self.gif_byte_array)
                self.gif_buffer.open(QtCore.QIODevice.ReadOnly)
                self.downloaded_cat_gif = QtGui.QMovie(self.gif_buffer)
                self.downloaded_cat_gif.setCacheMode(QtGui.QMovie.CacheAll)
                self.cat_image_label.setMovie(self.downloaded_cat_gif)
                self.downloaded_cat_gif.start()
                self.currently_displaying_gif = True

            else:
                # Loads other image files as a QPixmap.
                self.downloaded_cat_image = QtGui.QPixmap()
                self.downloaded_cat_image.loadFromData(self.catDownloadRead)
                self.cat_image_label.setPixmap(self.downloaded_cat_image)
                self.currently_displaying_gif = False

        self.setFixedSize(self.layout.sizeHint())
        self.new_cat_button.setText("New image")
        self.new_gif_button.setText("New GIF")
        self.loading_cat = False

    def import_cat(self):
        """Opens a file dialog to get the file location, then runs the downloading and importing function."""
        self.path_to_file = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save file", f"{COMPCAT_FOLDER_PATH}/{self.cat_parsed_JSON['file']}"
        )
    
        if self.path_to_file[0] == "":
            self.error_displayer.setText("CompCat couldn't download the cat image because the file path was not set correctly.")
        else:
            self._get_new_download_then_import_worker()

    def _get_new_download_then_import_worker(self):
        """Runs the download then import function on a seperate thread."""
        if not self.downloading_then_importing and self.has_cat_stored:
            self.error_displayer.setText("")
            self.worker = Worker(self._download_then_import)
            self.worker.signals.finished.connect(self._downloading_importing_done)
            self.threadpool.start(self.worker)
            self.import_button.setText("Downloading...")
            self.downloading_then_importing = True

    def _download_then_import(self):
        """Function that downloads the cat file to a location the user chooses."""

        try:
            urllib.request.urlretrieve(
                f"https://cataas.com{self.cat_parsed_JSON['url']}",
                f"{self.path_to_file[0]}",
            )
            self.has_succesfully_downloaded = True

        except PermissionError:
            self.has_succesfully_downloaded = False
            self.download_error = "CompCat couldn't import the cat because it doesn't have permission to write to the selected folder. Please pick another folder or change the folder's permission settings."

        except FileNotFoundError:
            self.has_succesfully_downloaded = False
            self.download_error = "CompCat couldn't download the cat to the set file path. Are you sure the folder path is correct?"

        except Exception as error:
            self.has_succesfully_downloaded = False
            self.download_error = f"Uh oh, something weird went wrong. Error: {error}. Please contact the dev if googling doesn't help."

    def _downloading_importing_done(self):
        """This function runs when the download then import function finishes. It is only for functions that update UI elements."""
        if self.has_succesfully_downloaded:
            read_node = nuke.createNode("Read")
            read_node.knob("file").fromUserText(f"{self.path_to_file[0]}")
        else:
            self.error_displayer.setText(self.download_error)

        self.import_button.setText("Import cat")
        self.setFixedSize(self.layout.sizeHint())
        self.downloading_then_importing = False


class Worker(QtCore.QRunnable):
    """Class for the QRunnable that runs a function on a seperate thread so Nuke doesn't freeze."""

    def __init__(self, function_to_run):
        super(Worker, self).__init__()
        self.function_to_run = function_to_run
        self.signals = WorkerSignals()

    @QtCore.Slot()
    def run(self):
        """Default function that gets executed by the QThreadPool."""
        self.function_to_run()
        self.signals.finished.emit()


class WorkerSignals(QtCore.QObject):
    """Signals for the QRunnable have to be stored seperately."""

    finished = QtCore.Signal()


def open_compcat_window():
    """Opens the CompCat window. Gets executed from the menu.py file."""
    CompCat_window = CompCatWindow()
    CompCat_window.show()
